import re


def extract_python_code(text: str) -> str:
    """
    Extracts Python code from markdown code blocks.
    """

    pattern = r"```python(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    if matches:
        return matches[0].strip()

    # fallback if generic ```
    pattern = r"```(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    if matches:
        return matches[0].strip()

    # if no markdown block, return original text
    return text.strip()
