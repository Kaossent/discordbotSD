from groq import AsyncGroq
from os import getenv
from dotenv import load_dotenv
from sys import exit

client = AsyncGroq(api_key="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")
model = "llama3-70b-8192"



async def generate_response(prompt, instructions, error, history=None):
    try:
        if history:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": prompt},
                    *history,
                ],
            )
        else:
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
