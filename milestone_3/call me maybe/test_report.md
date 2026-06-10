CALL ME MAYBE TEST REPORT
=========================
Date: 2026-06-06
Model download cached? (Y/N): Y

S1 Setup:            PASS
S2 Lint:             flake8+mypy PASS   strict PASS
S3 Baseline run:     EXIT0  output-existsYES  real_time_s62.62 (<300?)
S4 Schema validity:  JSON_OK COUNT_OK KEYS_OK NAME_OK PARAMS_OK
S5 Accuracy:         11/11 = 100% (>=90%)   misses listed below
  none
S6 Arg types:        TYPES_OK
S7 Error handling:   7a EXIT2 tb0  7b EXIT2 tb0  7c EXIT2 tb0  7d EXIT0 empty
S8 (validator used)

OVERALL: PASS only if S1,S2(lint),S3,S4(all OK),S5(>=90%),S6,S7(all) pass.
Failures / misses to escalate:
1.