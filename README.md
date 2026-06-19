# Regulatory Compliance Monitor

A small Streamlit prototype that turns technical CRC report errors into explanations and recommended actions that a Legal or Compliance team can understand.

## Run it

```powershell
python -m pip install -r requirements.txt
python generate_dataset.py
streamlit run main.py
```

The app opens in your browser. It uses the bundled synthetic dataset by default; no confidential or production data is needed.

## What the prototype demonstrates

- Counts of valid, problematic, and critical entries
- Charts for validation results, severity, and issue categories
- Plain-language explanations and recommended actions
- Filters, search, CSV upload, and analyzed-result download
- Edge cases including missing identifiers, invalid dates and amounts, duplicates, damaged payloads, timeouts, encoding failures, empty codes, and unknown errors

## Expected CSV columns

`timestamp`, `report_id`, `entity`, `source`, `error_code`, `technical_message`

This MVP uses a transparent rule catalog instead of an external AI service. In a production version, ELK could supply the logs and an approved language model could explain previously unseen errors, with human review for uncertain results.
