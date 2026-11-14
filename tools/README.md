# tools/

Standalone data-collection helpers. Standard library only. They are NOT part of the pipeline and are never run by the agent.

- `tcb_download.py` downloads the TCB daily Excel reports (pages 1-15 of tcb.gov.bd). Run by the user only; project rule: the agent never downloads from TCB.
- `tcb_convert.py` turns the downloaded Bangla Excel reports into one English CSV (the user's converter, with `--in` / `--out-csv` options added). Never overwrites a file.
- `tcb_append.py` adds newly converted report days to the existing price CSV. It accepts the converter's output directly, checks the columns, prices and duplicates, stops on any conflict, and never overwrites a file. With `--after-last-base-date` it uses only days later than the base file's last day, which protects the hand corrections. A longer panel changes the sample: log it in DEVIATIONS.md first.
- The full sequence (download, convert, append, hand over) and its checks are in `docs/DATA_COLLECTION.md`. Convert and append may be run by the agent on the work PC; downloading may not.
- `comtrade_bd_food_imports.py` builds the monthly Comtrade import table (public preview API, or a free key in COMTRADE_KEY). Run by the user only.

Outputs go to inbox/ (never straight into data/raw/); S00 intake copies and hashes them.
