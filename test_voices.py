import asyncio
import edge_tts

async def list_voices():
    voices = await edge_tts.list_voices()
    indian_voices = []
    for voice in voices:
        locale = voice['Locale']
        if 'en-IN' in locale or 'hi-IN' in locale or 'mr-IN' in locale:
            indian_voices.append({
                'name': voice['ShortName'],
                'locale': voice['Locale'],
                'gender': voice['Gender'],
                'friendly_name': voice['FriendlyName']
            })

    print('Available Indian language voices:')
    for voice in indian_voices:
        print(f"- {voice['name']} ({voice['locale']}) - {voice['gender']}")

asyncio.run(list_voices())