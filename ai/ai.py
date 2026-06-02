from groq import AsyncGroq
from os import getenv
from dotenv import load_dotenv
from sys import exit

client = AsyncGroq(api_key="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")
model = "llama3-70b-8192"



async def generate_response(prompt, instructions, error):
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            )

        return response.choices[0].message.content
    except Exception as e:
        print(f"Не смог сгенерировать запрос.")
        return error
