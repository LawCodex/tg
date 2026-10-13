# Togo (TG) — législation en Markdown

Part of [LawCodex](https://github.com/LawCodex): the legislation of every country as plain Markdown in git.

Laws of the Togolese Republic, in **French** (official language), as published in the **Journal officiel de la
République togolaise** on its official website https://jo.gouv.tg (section "Lois"). Texts are as enacted (not
consolidated), cut out of the Journal officiel issues.

Retrieved 2026-10-13.

<!-- COUNTS -->
<!-- /COUNTS -->

## Structure

```
lois/<year>/loi-<year>-<nnn>.md                     ordinary laws
lois-organiques/<year>/loi-<year>-<nnn>.md          organic laws
lois-constitutionnelles/<year>/loi-<year>-<nnn>.md  constitutional laws (incl. the Constitution of 6 May 2024)
```

`<year>` is the year of the law's date. Front matter: `identifier` = law number; `date` = date of the law as given
by the JO website; `source` = Journal officiel PDF with the start page (`#page=N`); `record` = the JO website page
of the law; `gazette` = the JO issue file name (year of publication, issue number, "BIS" for special issues);
`status: unknown` (the source does not track repeal/amendment).

Each law is extracted from its Journal officiel issue: the text starts at the heading "LOI N° …" matching the law
number and ends at the next heading of another text (decree, order, other law…). Headings: TITRE / CHAPITRE /
SECTION → `##`…; articles → headings. JO pages are laid out in two columns; poppler's reading order is used, and
scanned issues (mostly before ~2010) were OCRed with tesseract (French) — see `note`.

## Source

| Source | URL |
|---|---|
| Journal officiel de la République togolaise — Lois | https://jo.gouv.tg/Lois (89 listing pages, one entry per law with a link to the JO PDF) |

robots.txt of jo.gouv.tg asks for `Crawl-delay: 10`; the scripts wait 10 s between requests.
The site's "about" page cites loi n° 2016-006 du 30 mars 2016 on freedom of access to information and public
documents as the basis of the online publication.

## Not covered / known gaps

* Only the "Lois" section is covered (≈970 entries). The "Actes du Gouvernement" section (ordinances, decrees,
  arrêtés — ≈9,700 entries) was not crawled (mass secondary legislation; with the required 10 s crawl delay it
  would take ~30 hours just to list). Ordinances are therefore missing.
* Entries whose JO PDF is missing, or where the law heading could not be located in the issue (OCR errors,
  unusual layout), are skipped; the fetch script reports them (`NOTFOUND`, `MISSING/BAD`).
* Two-column layout: where poppler mixes columns, sentences may be out of order; OCR texts contain recognition
  errors. Tables are flattened to text.

## Copyright

Official texts of the Togolese Republic published by the Journal officiel service for public access; no reuse
restriction is stated. The Markdown conversion is provided as is; the authoritative text is the printed Journal
officiel.

## Regenerating

```sh
python3 scripts/tg_fetch.py     # lists, downloads (10 s crawl delay) to ../_raw/tg/ and writes the Markdown
python3 scripts/tg_readme.py    # updates the counts table
```
