# English keyboard resource manifest

Resource identity is byte-addressed. These hashes are SHA-256 over the exact UTF-8 bytes committed in this repository.

| Resource | Declared identity | SHA-256 | Notes |
|---|---|---|---|
| `en_US.dic` | LibreOffice `en_US` Hunspell dictionary; SCOWL 2020.12.07-derived; header declares 49,568 entries | `f0b1a234bd178bdd01875b2a392a9647f888b8fe879f79c52aae62c2759b3647` | 551,762 bytes; exact resource bytes are pinned; the count is validated at load time |
| `en_US.aff` | Matching `en_US` affix resource; UTF-8; no independent release string is declared | `e746c882dd6f303c2c46e7452804b9201115a6942cfeb15f18f8edf774d2e24e` | 3,205 UTF-8 bytes; exact resource bytes are pinned; parser support is deliberately narrower than full Hunspell |

## Provenance and licensing

The upstream attribution and redistribution terms are preserved verbatim in `README_en_US.txt`. Do not remove or replace that file when redistributing the dictionary resources. The source family is the LibreOffice `dictionaries` English (United States) Hunspell resource set, derived from SCOWL.

## Implemented parser profile

- UTF-8 dictionary and affix input.
- Declared dictionary-entry count checked against parsed entries.
- Single-character affix flags.
- Prefix and suffix rules with conditions anchored to the correct word edge.
- `NOSUGGEST` entries remain valid words but are not offered as suggestions.
- `ONLYINCOMPOUND` roots are excluded from standalone validity and suggestions because compound composition is not implemented.
- Personal vocabulary and rejected-suggestion overlays are stored separately from the bundled dictionary.

## Explicit limitations

This is not a complete Hunspell implementation. It does not implement `COMPOUNDRULE` composition, continuation-class chaining, or the full set of Hunspell directives. It must not be described as full Hunspell compatibility. The supported parser profile is the one above; unsupported constructs fail closed or remain unexpanded rather than being silently treated as complete support.
