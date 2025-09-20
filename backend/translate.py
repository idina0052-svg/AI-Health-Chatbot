from deep_translator import GoogleTranslator

def translate_text(text, source="auto", target="en"):
    """Translate text using free Google Translate (deep-translator)"""
    try:
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception as e:
        print("Translation error:", e)
        return text  
