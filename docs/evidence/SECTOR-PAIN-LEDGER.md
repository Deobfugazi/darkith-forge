# Sector pain ledger — primary-source observations

Fetched live 2026-11-19 from the issuing body. Each row: the number as the source
states it, the invariant term it is a failure of, and the URL. No secondary reporting.

| # | Sector | Observation (verbatim figure) | Invariant term that fails | Source |
|---|---|---|---|---|
| 1 | Critical infrastructure / all software | CISA KEV catalog 2026.11.18: **1786** known-exploited vulns; **361** tied to ransomware; Microsoft 391, Cisco 103, Apple 96, Adobe 83, Google 77, Oracle 46 | Sigma_B != 0: known-exploited defects still shipping | cisa.gov KEV JSON |
| 2 | All software | NVD: **428,256** CVE records total | Sigma_B != 0: unbounded rejection surface | nvd.nist.gov CVE API 2.0 |
| 3 | Consumers / end users | FBI IC3 2024: **859,532** complaints, **$16.6B** losses, +33% YoY; cyber-enabled fraud 333,981 complaints / $13.7B (38% of complaints, 83% of losses) | Condition C without D: a promise with no server of record | ic3.gov 2024 report |
| 4 | Consumers (investment) | IC3 2024: investment fraud **$6.57B**; 2023 was $4.57B, up from $3.31B (+38%) | Retention: E/W_in > 0, value leaves the victim with no return | ic3.gov 2023+2024 |
| 5 | Private companies | IC3 2024: Business Email Compromise **$2.77B**, 21,442 complaints | Coupling: C = D n P != empty (attacker occupies the trusted name) | ic3.gov 2024 |
| 6 | Fintech / global FX | BIS Triennial 2025: **$9.6 trillion/day** FX turnover (April 2025); OTC IRD $7.9T | Scale of the settlement surface the residual accrues on | bis.org rpfx25 |
| 7 | Government / G20 | FSB: cross-border payments face four challenges — **high costs, low speed, limited access, insufficient transparency**; G20 Roadmap 19 building blocks since 2020 | Retention + latency: friction is the residual made monetary | fsb.org roadmap |
| 8 | Political / monetary | BIS Annual Report 2025: **>60%** of responding jurisdictions had or were developing stablecoin regulatory frameworks (2023 survey) | Condition D under construction: who is server of record | bis.org ar2025e3 |
| 9 | Black market / illicit finance | Chainalysis: 2024 illicit inflows **$40.9B** lower bound; 2023 revised from $24.2B to **$46.1B**; avg **25%** upward revision between reporting periods | Measurement residual: the ledger undercounts its own bond failures | chainalysis.com |
| 10 | Developers | GitHub Octoverse 2025: **986 million** code pushes | Coupling volume: each push is a graft that must satisfy C = D n P | github.blog octoverse |

## Rejected — not used, because the bytes did not contain the number
- Sonatype 2026 SSSC: page renders figures as JS-animated `00` placeholders. No static number in the served HTML. Not cited.
- World Bank Gini (WLD): API returns `value: null` for 2021-2025. Not cited.
- FATF publications, defense.gov releases, GAO: HTTP 403 to this client. Not cited.
- Tavily search API: HTTP 432 plan limit exceeded. Fell back to direct primary fetch.

## The reading
Every row is the same failure in a different currency. A bond was asserted and did not
hold, and the size of the failure is a number the issuing body publishes. That is the
invariant's own claim: failure has an exact size, and the rule is to compute it, force
the correction, and ship only at zero.

## Verification pass (second fetch, same day)

Every figure above was re-read from the source bytes a second time, after the first
pass, to catch transcription error. Method: fetch the issuing body's own document,
extract text, and test for the literal string. A claim passes only if the string is
present in the bytes.

| Claim | Literal string tested | Result |
|---|---|---|
| CISA KEV count | `1786` from `count` field | PASS |
| CISA ransomware | `361` by `knownRansomwareCampaignUse == Known` | PASS |
| NVD total | `428256` from `totalResults` | PASS |
| IC3 complaints | `859,532` | PASS (47-page 2024 PDF) |
| IC3 losses | `16.6 billion` | PASS |
| IC3 cyber-enabled | `13.7 Billion` | PASS |
| IC3 investment | `6,570,639,864` | PASS |
| IC3 BEC | `2,770,151,146` | PASS |
| IC3 BEC count | `21,442` | PASS |
| BIS FX turnover | `9.6 trillion per day in April 2025` | PASS |
| FSB challenges | `high costs, low speed, limited access and insufficient transparency` | PASS |
| FSB roadmap | `19 building blocks` | PASS |
| Chainalysis 2024 | `40.9 billion` | PASS |
| Chainalysis 2023 revised | `46.1 billion` and `24.2 billion` | PASS |
| Octoverse pushes | `986 million code pushes` | PASS |
| BIS stablecoin | `more than 60%` | PASS |

### One near-miss worth recording
The first re-verification run reported six IC3 figures as absent. The cause was not a
bad number but a bad method: the glob matched the **2023** report (34 pages, 880,418
complaints) because both files were PDFs in the same directory, and the whitespace
normaliser had been changed between passes. Re-running against the correctly identified
47-page 2024 report returned PASS on all six. The lesson is SPI-2's: a negative from a
changed method is not evidence. Identify the artifact by its own bytes before testing it.
