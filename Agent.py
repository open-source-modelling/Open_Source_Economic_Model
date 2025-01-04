import ollama


def ollama_bigger(value):
    content = f"Is float {value} bigger than 0? Y or N. Do not write code. Just the correct letter."
#        print(content)
    response = ollama.chat(model="llama3.2", messages=[
    {
        "role": "user",
        "content": content
    },
    ])
    return response
    
