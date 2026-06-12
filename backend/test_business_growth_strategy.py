import json

import requests


URL = "http://localhost:5000/api/generate_business_growth_strategy"
CONTEXT = "We are a B2B SaaS company selling AI-powered project management software to creative agencies."
WEBSITE = "https://example.com"
FILES = [
    (
        "transcripts",
        (
            "sales_call_1.txt",
            "Customer: We struggle with deadlines. Sales: Our AI predicts delays.",
            "text/plain",
        ),
    )
]

DATA = {
    "context": CONTEXT,
    "website": WEBSITE,
}


def main():
    print("Sending request to generate Business Growth Strategy...")
    try:
        response = requests.post(URL, data=DATA, files=FILES, stream=True, timeout=300)
        if response.status_code != 200:
            print(f"FAILED (Status {response.status_code}): {response.text}")
            return

        complete_payload = None
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            event = json.loads(raw_line)
            if event.get("type") == "complete":
                complete_payload = event.get("business_growth_strategy") or event.get("game_plan")
                break
            if event.get("type") == "error":
                print(f"FAILED (Pipeline Error): {event.get('message')}")
                return

        if complete_payload:
            print("\nSUCCESS! Business Growth Strategy generated:")
            print(json.dumps(complete_payload, indent=2)[:500] + "\n... (truncated)")
        else:
            print("FAILED: Stream ended without complete payload.")
    except Exception as error:
        print(f"FAILED (Exception): {error}")


if __name__ == "__main__":
    main()
