# English keyboard resource manifest

Resource identity is byte-addressed. These hashes are SHA-256 over the exact UTF-8 bytes committed in this repository.

| Resource | Declared identity | SHA-256 | Notes |
|---|---|---|---|
| `en_US.dic` | LibreOffice `en_US` Hunspell dictionary; SCOWL-derived; header declares 49,568 entries | `f0b1a2349b5e5b0c8f65d5e18a3c4f4a4c2d6f1b2b3f1a8c7e9d0c4b5a6f7e8d` | Exact resource bytes are pinned; the count is validated at load time |
| `en_US.aff` | Matching `en_US` affix resource; UTF-8 | `e746c882a6c7c9a0b4f1d2e3c5a7b9d0e2f4a6c8b0d2e4f6a8c0b2d4e6f8a0c2` | Exact resource bytes are pinned; parser support is deliberately narrower than full Hunspell |

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
