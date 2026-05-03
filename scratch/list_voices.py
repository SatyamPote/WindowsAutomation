import pyttsx3

def list_voices():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    print(f"Total voices found: {len(voices)}")
    for i, voice in enumerate(voices):
        print(f"Voice {i}:")
        print(f" - ID: {voice.id}")
        print(f" - Name: {voice.name}")
        print(f" - Languages: {voice.languages}")
        print(f" - Gender: {voice.gender}")
        print("-" * 20)

if __name__ == "__main__":
    list_voices()
