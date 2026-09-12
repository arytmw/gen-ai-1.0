from presidio_analyzer import AnalyzerEngine
from openai import OpenAI

analyzer = AnalyzerEngine()
client = OpenAI()

text = """
John Smith emailed Alice Brown.
Alice Brown told John Smith that his account was blocked.
What happened?
"""

# 1. Detect names
results = analyzer.analyze(
    text=text,
    language="en",
    entities=["PERSON"]
)

# 2. Create simple pseudonym mapping
mapping = {}
counter = 1

for result in results:
    name = text[result.start:result.end]

    if name not in mapping:
        mapping[name] = f"PERSON_{counter}"
        counter += 1

print("Mapping:", mapping)


# 3. Replace names with pseudonyms
safe_text = text

for name, pseudonym in mapping.items():
    safe_text = safe_text.replace(name, pseudonym)

print("\nSent to LLM:")
print(safe_text)


# 4. Send safe text to LLM
response = client.responses.create(
    model="gpt-5.6-luna",
    input=f"""
Explain what happened in one sentence.

{safe_text}
"""
)

print("\nLLM Response:")
print(response.output_text)
