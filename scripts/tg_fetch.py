#!/usr/bin/env python3
"""Togo: laws listed on the official Journal officiel website (https://jo.gouv.tg/Lois).

Each listing entry gives the law number, date, subject and a link to the Journal officiel PDF
(with the start page). The JO issue is downloaded, its text extracted (OCR with tesseract
'fra' for scanned pages) and the law is cut out of the issue, from its heading
("LOI N° ...") to the heading of the next text.
robots.txt asks for Crawl-delay: 10 -> every request is spaced by 10 s.
Usage: python3 tg_fetch.py [--no-download]"""
import html
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tg_text as T  # noqa

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(os.path.dirname(REPO), "_raw", "tg")
BASE = "https://jo.gouv.tg"
DELAY = 10
RETRIEVED = os.environ.get("LC_RETRIEVED", "2026-10-13")
os.environ.setdefault("LC_TESSDATA", os.path.join(RAW, "tessdata"))
os.environ.setdefault("LC_PSM", "3")  # two-column JO scans


def listing():
    path = os.path.join(RAW, "lois.json")
    if os.path.exists(path) and "--relist" not in sys.argv:
        return json.load(open(path))
    rows = []
    page = 0
    last = None
    while True:
        dest = os.path.join(RAW, "list", "%d.html" % page)
        T.fetch(BASE + "/Lois" + ("?page=%d" % page if page else ""), dest, delay=DELAY)
        s = open(dest, encoding="utf-8", errors="replace").read()
        if last is None:
            m = re.search(r'href="/Lois\?page=(\d+)"[^>]*>\s*dernier', s)
            last = int(m.group(1)) if m else 0
        for blk in re.split(r'<div class="views-row', s)[1:]:
            m = re.search(r'href="/?(node/\d+)">(.*?)</a>', blk, re.S)
            if not m:
                continue
            label = html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", m.group(2)))).strip()
            d = re.search(r'content="(\d{4}-\d{2}-\d{2})', blk)
            subj = re.search(r'field-en-tete">\s*<div class="field-content">(.*?)</div>', blk, re.S)
            pdf = re.search(r'href="([^"]+\.pdf)(#page=(\d+))?"', blk, re.I)
            rows.append({"node": m.group(1), "label": label, "date": d.group(1) if d else None,
                         "subject": html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", subj.group(1)))).strip() if subj else "",
                         "pdf": html.unescape(pdf.group(1)) if pdf else None,
                         "page": int(pdf.group(3)) if pdf and pdf.group(3) else 1})
        page += 1
        if page > last:
            break
    json.dump(rows, open(path, "w"), ensure_ascii=False, indent=1)
    return rows


HEAD = re.compile(r"^(LOI|Loi|DECRET|DÉCRET|Décret|ORDONNANCE|Ordonnance|ARRETE|ARRÊTÉ|Arrêté|DECISION|DÉCISION|Décision)"
                  r"\s+(ORGANIQUE\s+|organique\s+|CONSTITUTIONNELLE\s+|constitutionnelle\s+|UNIFORME\s+|uniforme\s+|INTERMINISTERIEL\s+|interministériel\s+)?[Nn]\s*[°o*º]?\s*([0-9]{2,4}\s*[-–—]\s*[0-9]+)", re.U)


def numkey(s):
    s = re.sub(r"\s", "", s).replace("–", "-").replace("—", "-")
    a, b = s.split("-", 1)
    return "%s-%03d" % (a[-2:], int(re.match(r"\d+", b).group(0)))  # 2-digit year: "04-03" == "2004-03"


def cut(pages, start_page, num):
    """Return the lines of the law `num` (e.g. '2025-004') from the JO pages."""
    if start_page > len(pages):
        start_page = 1  # extracts ("Pages from jo ...") keep the page number of the full JO issue
    lines = T.clean_pages(pages[max(0, start_page - 2):])  # listing page numbers are sometimes one page late
    lines = [re.sub(r"^[^\wÀ-ÿ]+(?=(LOI|Loi)\b)", "", x) for x in lines]
    want = numkey(num) if num else None
    start = None
    for i, x in enumerate(lines):
        m = HEAD.match(x)
        if m and m.group(1).upper().startswith("LOI") and (want is None or numkey(m.group(3)) == want):
            # skip the table of contents (followed by lines starting with dates)
            nxt = " ".join(lines[i:i + 8])
            if "délibéré" in nxt or "promulgue" in nxt or "adopté" in nxt or start is None:
                start = i
                if "délibéré" in nxt or "promulgue" in nxt:
                    break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        m = HEAD.match(lines[j])
        if m and (m.group(1).upper() not in ("LOI",) or numkey(m.group(3)) != (want or numkey(HEAD.match(lines[start]).group(3)))):
            end = j
            break
    return lines[start:end]


def _extract(path):
    if T.pdf_ok(path):
        tmp = os.path.join(RAW, "ocr", os.path.basename(path))
        os.makedirs(tmp, exist_ok=True)
        T.pdf_text_columns(path, "fra", tmpdir=tmp)
    return path


def prewarm(n):
    """Extract text (OCR) of all downloaded JO PDFs in parallel; cached next to the PDFs."""
    from concurrent.futures import ProcessPoolExecutor
    d = os.path.join(RAW, "pdf")
    paths = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith(".pdf"))
    with ProcessPoolExecutor(n) as ex:
        for k, _ in enumerate(ex.map(_extract, paths)):
            if k % 20 == 0:
                print("extracted", k, "/", len(paths), flush=True)


def main():
    if "--jobs" in sys.argv:
        prewarm(int(sys.argv[sys.argv.index("--jobs") + 1]))
        if "--prewarm-only" in sys.argv:
            return
    rows = listing()
    print("listed", len(rows), flush=True)
    used = {}
    n = 0
    for r in rows:
        if not r["pdf"]:
            print("NOPDF", r["label"])
            continue
        fn = urllib.parse.unquote(r["pdf"].rsplit("/", 1)[1])
        dest = os.path.join(RAW, "pdf", T.slug(fn[:-4], 120) + ".pdf")
        if "--no-download" not in sys.argv:
            T.fetch(r["pdf"], dest, delay=DELAY, check_pdf=True, timeout=300)
        if not os.path.exists(dest) or not T.pdf_ok(dest):
            print("MISSING/BAD", r["pdf"], flush=True)
            continue
        if "--download-only" in sys.argv:
            continue
        pages, ocr = T.pdf_text_columns(dest, "fra", tmpdir=RAW)
        m = re.search(r"(\d{4}|\d{2})\s*[-–—]\s*(\d+)", r["label"])
        num = "%s-%s" % (m.group(1), m.group(2)) if m else None
        seg = cut(pages, r["page"], num)
        if not seg:
            print("NOTFOUND", r["label"], fn, r["page"], flush=True)
            continue
        organique = "organique" in r["label"].lower() or "ORGANIQUE" in seg[0]
        constit = ("constitution" in r["label"].lower() or "CONSTITUTIONNELLE" in seg[0]
                   or re.search(r"(portant|r[ée]vision de la|modifiant la|compl[ée]tant la)\s+constitution", r["subject"], re.I))
        # heading lines: "LOI N° ... du ..." + subject lines until the enacting formula
        k = 1
        while k < min(len(seg), 10) and not re.search(r"délibéré|promulgue|adopté|^Article|^ARTICLE", seg[k]):
            k += 1
        head = " ".join(x for x in seg[:k] if x)
        title = re.sub(r"\s+", " ", head).strip()
        if len(title) > 400:
            title = (r["label"] + " " + r["subject"]).strip()
        body = T.structure(seg[k:], "fr")
        if sum(len(x) for x in body) < 150:
            print("SHORT", r["label"], flush=True)
            continue
        year = (r["date"] or (num or "undated"))[:4]
        cat, typ = ("lois-constitutionnelles", "constitutional_law") if constit else \
            (("lois-organiques", "organic_law") if organique else ("lois", "act"))
        rel = "%s/%s/loi-%s.md" % (cat, year, num or T.slug(r["label"]))
        if rel in used:
            rel = rel[:-3] + "-" + r["node"].split("/")[1] + ".md"
        used[rel] = 1
        meta = {"title": title, "identifier": ("Loi n° %s" % num) if num else r["label"], "type": typ,
                "jurisdiction": "tg", "language": "fr", "date": r["date"], "status": "unknown",
                "source": r["pdf"] + "#page=%d" % r["page"], "record": BASE + "/" + r["node"],
                "gazette": re.sub(r"\.pdf$", "", fn), "retrieved": RETRIEVED,
                "note": "Extracted from the Journal officiel issue (as enacted)" + ("; OCR" if ocr else "")}
        T.write_md(os.path.join(REPO, rel), meta, title, body)
        n += 1
        print("OK", rel, flush=True)
    print("written", n)


if __name__ == "__main__":
    main()
