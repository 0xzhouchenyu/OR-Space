# Exact-match normalization

The public scorer applies the following deterministic normalization before
matching a required entity:

1. Unicode NFKC normalization.
2. Curly quote, dash, minus, and arrow normalization.
3. Removal of Markdown backticks and collapse of whitespace.
4. Removal of thousands separators between digits.
5. Case folding.

Identifier-like entities use non-identifier boundaries, so the target `I`
does not match the `I` inside `II` or an ordinary word. Structured symbols are
also compared in a compact representation that ignores quote/space variation
and treats square and round index brackets equivalently. Pure numeric targets
allow a `1e-6` relative tolerance (`1e-9` absolute) after numeric parsing.

The implementation of record is
`evaluation_programs/explain/score_explain.py::entity_hit`. The output retains every
entity decision as `c<criterion>.e<entity>` so users can audit the score.
