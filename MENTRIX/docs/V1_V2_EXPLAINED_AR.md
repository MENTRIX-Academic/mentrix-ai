# V1 versus V2: Code-level explanation — for the AI team

## Is V1 an AI model? No.
Both are successive **versions of typed-answer grading rules/pipelines**. `grader.py` implements a Strict baseline plus Type-aware V1. `grader_v2.py` implements Type-aware V2; it imports helpers from V1. No fine-tuning, OCR, handwriting or model inference occurs in either grader.

## Strict baseline
- MCQ: exact raw letter vs `correct_letter`.
- Short: exact raw answer vs `canonical_answer`.
- Math: exact raw expression plus unit vs canonical text.
- Result choices: `correct`, `incorrect` or `review` (unsupported question type). This baseline frequently rejects alternative valid spellings.

## V1 = grade(question, answer, baseline='type_aware')
- MCQ: Regex matches a single A-D letter optionally wrapped in `option` / parentheses / dot. `Answer: B` isn't supported; goes review.
- Short: Unicode normalization (NFKC, casefold), hyphens/punctuation/whitespace, aliases, maximum word count. Unlisted answers near accepted spelling are reviewed (SequenceMatcher ≥ 0.79), otherwise immediately **incorrect**; this risks rejecting valid unlisted abbreviations.
- Math: restricted Python AST *without eval*, allowlisted functions/units, SymPy equivalence, numeric tolerance `max(1e-9,1e-9*abs(reference))`. Some near misses can be accepted; some cancellations can change domain. AST is a safety-minded prototype, **not a hardened sandbox**.

## V2 = grade_v2(question, answer)
- MCQ: matches `Answer: B`, `Option B`, a clear single letter and marks multiple/ambiguous inputs review.
- Short: approved aliases → correct; educator-configured KNOWN_WRONG list → incorrect; all unknown short answers/abbreviations/typos → review. Question mark explicitly → review. This reduces premature auto-rejections but increases TA workload.
- Math: V2 checks possible symbolic denominator/domain risk before simplified comparison, then **calls V1's math verifier**, then re-checks numeric differences more strictly. Tiny nonzero numeric differences become review until the TA sets a precision policy. Power notation `x²` and limited `2x` rewrite supported. Not a general symbolic theorem prover; special-case logic for MA05 (`1/f`) should be generalized before production.
- Descriptive: `ESSAY_SEPARATE` → review. The previous TF-IDF/SBERT/NLI research pipeline is **not plugged into this app**.

## Real run from original code (see research/results/observed_comparison.csv)
| Example | Strict | V1 | V2 | Explanation |
|---|---|---|---|---|
| MC01 / `Answer: B` | incorrect | review | correct | V2 supports explicit answer prefix |
| SA02 / `Frequency.` | incorrect | correct | correct | normalized punctuation/case |
| SA02 / `freq` | incorrect | incorrect | review | unlisted abbreviation might be valid |
| SA02 / `period` | incorrect | incorrect | incorrect | listed known-wrong contrast |
| MA03 / `2.000000001 Hz` | incorrect | correct | review | V1 tolerance vs V2 conservative precision |
| MA04 / `x²+2x+1` | incorrect | review | correct | V2 limited notation normalization |
| MA04 / `x^2+2*x+(x-1)/(x-1)` | incorrect | correct | review | domain cancellation x=1 |

## Trade-off
V2 is not independently proven more accurate: on the historical **123 authored** test cases V2 was revised against the same cases; matching 123/123 is *regression/design agreement*, NOT real student accuracy. It sent 51/123 (41.5%) to TA review vs V1's 38/123. This may be safer but adds workload.
