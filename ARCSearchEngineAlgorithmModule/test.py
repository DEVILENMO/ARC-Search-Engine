import json

input = """
    {
        "content": "['ababa', 'dddd']"
    }
    """

data = json.loads(input)
content = eval(data.get('content', ''))
print(content)
for c in content:
    print(c)