import pyttsx3

def test_voices():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    print(f"Total voices found: {len(voices)}")
    for i, voice in enumerate(voices):
        print(f"[{i}] Name: {voice.name}")
        print(f"    ID: {voice.id}")
        print(f"    Languages: {voice.languages}")
        print(f"    Gender: {voice.gender}")
        print("-" * 20)

if __name__ == "__main__":
    test_voices()
