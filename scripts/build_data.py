#!/usr/bin/env python3
"""Build tiny, 3-digit-prefix JSON shards from Japan Post's public postcode ZIPs.

Stdlib-only. Designed for GitHub Actions + GitHub Pages. Supports local ZIPs for tests.
"""
import argparse
import csv
import datetime as dt
import io
import json
import re
import shutil
import time
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDARD_URLS = [
    'https://www.post.japanpost.jp/service/search/zipcode/download/utf/zip/utf_ken_all.zip',
    'https://raw.githubusercontent.com/hiroyuki-komatsu/japanpost_zipcode/main/utf_ken_all.zip',
]
OFFICE_URLS = [
    'https://www.post.japanpost.jp/service/search/zipcode/download/office/zip/jigyosyo.zip',
    'https://raw.githubusercontent.com/hiroyuki-komatsu/japanpost_zipcode/main/jigyosyo.zip',
]
ZIP_RE = re.compile(r'^\d{7}$')


def download_zip(urls, label):
    problems = []
    for url in urls:
        for attempt in range(1, 3):
            try:
                print(f'Download {label} attempt {attempt}: {url}', flush=True)
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; JapanPostStaticLookup/1.0)',
                    'Accept': 'application/zip,application/octet-stream,*/*'
                })
                with urllib.request.urlopen(req, timeout=60) as resp:
                    body = resp.read()
                with zipfile.ZipFile(io.BytesIO(body)) as zf:
                    members = [x for x in zf.namelist() if x.lower().endswith('.csv')]
                    if not members:
                        raise ValueError('ZIP has no CSV')
                print(f'Downloaded {label}: {len(body):,} bytes', flush=True)
                return body, url
            except Exception as exc:
                problems.append(f'{url} (attempt {attempt}): {type(exc).__name__}: {exc}')
                if attempt == 1:
                    time.sleep(2)
    raise RuntimeError('Unable to download '+label+'\n'+'\n'.join(problems))


def iter_csv(blob, encoding):
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        csv_names = [name for name in zf.namelist() if name.lower().endswith('.csv')]
        if not csv_names:
            raise ValueError('ZIP did not contain a CSV')
        with zf.open(csv_names[0]) as raw:
            with io.TextIOWrapper(raw, encoding=encoding, newline='') as stream:
                yield from csv.reader(stream)


def build(address_zip, office_zip, out_dir, address_url, office_url, allow_small=False):
    out_dir = Path(out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    static_dir = ROOT / 'web'
    for file in ('index.html', 'app.js', 'style.css'):
        shutil.copy2(static_dir / file, out_dir / file)
    (out_dir / '.nojekyll').write_text('', encoding='utf-8')
    shard_dir = out_dir / 'data'
    shard_dir.mkdir(exist_ok=True)

    # Each ZIP prefix file maps the final four postcode digits to an array of
    # matches. Normal entries: [prefecture, municipality, town]. Business
    # entries add [business name, block/detail, 'office'] at positions 3..5.
    shards = defaultdict(lambda: defaultdict(list))
    prefectures = set()
    general_rows = 0
    office_rows = 0
    invalid_rows = 0
    for row in iter_csv(address_zip, 'utf-8-sig'):
        if len(row) < 9 or not ZIP_RE.fullmatch(row[2]):
            invalid_rows += 1
            continue
        zip7 = row[2]
        pref, city, town = [v.strip() for v in row[6:9]]
        if not (pref and city):
            invalid_rows += 1
            continue
        # The postcode data's no-specific-town sentinel isn't part of an address.
        if town == '以下に掲載がない場合':
            town = ''
        record = [pref, city, town]
        matches = shards[zip7[:3]][zip7[3:]]
        if record not in matches:
            matches.append(record)
        prefectures.add(pref)
        general_rows += 1

    for row in iter_csv(office_zip, 'cp932'):
        if len(row) < 8 or not ZIP_RE.fullmatch(row[7]):
            invalid_rows += 1
            continue
        zip7 = row[7]
        company = row[2].strip()
        pref, city, town, detail = [v.strip() for v in row[3:7]]
        if not (pref and city):
            invalid_rows += 1
            continue
        record = [pref, city, town, company, detail, 'office']
        matches = shards[zip7[:3]][zip7[3:]]
        if record not in matches:
            matches.append(record)
        office_rows += 1
        prefectures.add(pref)

    if not allow_small:
        if general_rows < 100000 or office_rows < 10000 or len(prefectures) < 47:
            raise RuntimeError(
                f'Incomplete Japan data: general={general_rows}, office={office_rows}, '
                f'prefectures={len(prefectures)} (expected >=100000, >=10000, 47).'
            )

    total_bytes = 0
    for prefix, by_tail in sorted(shards.items()):
        file = shard_dir / f'{prefix}.json'
        payload = json.dumps(by_tail, ensure_ascii=False, separators=(',', ':'))
        file.write_text(payload, encoding='utf-8')
        total_bytes += file.stat().st_size

    metadata = {
        'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'address_source': address_url,
        'office_source': office_url,
        'address_records': general_rows,
        'office_records': office_rows,
        'prefectures': len(prefectures),
        'postal_codes': sum(len(x) for x in shards.values()),
        'prefix_files': len(shards),
        'json_bytes': total_bytes,
        'invalid_rows_skipped': invalid_rows,
        'dataset_note': 'Town-level address; building/unit/house number must be entered by user.'
    }
    (shard_dir / 'meta.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print('DONE '+json.dumps(metadata, ensure_ascii=False, indent=2), flush=True)
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default=str(ROOT / 'public'))
    parser.add_argument('--address-zip', type=Path, help='Use a pre-downloaded ZIP for general addresses')
    parser.add_argument('--office-zip', type=Path, help='Use a pre-downloaded ZIP for business postcodes')
    parser.add_argument('--allow-small', action='store_true', help='Only for tests with fixture data')
    args = parser.parse_args()

    if args.address_zip:
        address_blob = args.address_zip.read_bytes()
        address_url = str(args.address_zip)
    else:
        address_blob, address_url = download_zip(STANDARD_URLS, 'general addresses')
    if args.office_zip:
        office_blob = args.office_zip.read_bytes()
        office_url = str(args.office_zip)
    else:
        office_blob, office_url = download_zip(OFFICE_URLS, 'office postcodes')
    build(address_blob, office_blob, args.out, address_url, office_url, args.allow_small)


if __name__ == '__main__':
    main()
