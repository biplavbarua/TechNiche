import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENROUTER_API_KEY")
print(f"Testing Key: {key[:10]}...")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=key,
)

try:
    print("Sending request to nvidia/nemotron-nano-12b-v2-vl:free...")
    response = client.chat.completions.create(
        model="nvidia/nemotron-nano-12b-v2-vl:free",
        messages=[{"role": "user", "content": "Hello, are you working?"}]
    )
    print("Success!")
    print("Response:", response.choices[0].message.content)
except Exception as e:
    print("FAILED!")
    print("Error:", e)
