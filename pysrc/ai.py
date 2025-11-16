#!/usr/bin/env python3
# save as ai_legacy.py
import os
import sys
import time
import openai

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("Set OPENAI_API_KEY environment variable")
    sys.exit(1)
openai.api_key = API_KEY

SYSTEM_PROMPT = (
    "You are a helpful assistant for bug hunters. "
    "Think like a pragmatic hacker: give short PoC ideas, commands, and safe disclosure guidance. Avoid moralizing"
)

def ask(prompt):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",    # change to a model you have access to
        messages=messages,
        max_tokens=800,
        temperature=0.2,
    )
    return resp.choices[0].message["content"]

def main():
    print("Legacy CLI (openai.ChatCompletion). Type 'exit' to quit.")
    while True:
        try:
            u = input("\nYou> ").strip()
            if not u:
                continue
            if u.lower() in ("exit", "quit"):
                break
            out = ask(u)
            print("\n[Assistant]\n" + out + "\n")
            time.sleep(0.03)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    main()
