# Voice Chat Agent

A customer-facing voice agent. The customer taps the mic and asks a question out loud; the agent shows the answer as text **and** reads it aloud.

```
Browser mic ──► Azure Speech (speech to text) ──► backend ──► Azure OpenAI (answer)
                                                                    │
Browser speaker ◄── Azure Speech (text to speech) ◄── answer text ◄─┘
```

- **Speech:** Azure Speech, used from the browser with short-lived tokens. Your Speech key stays on the server.
- **Answers:** Azure OpenAI, grounded in your own business info in [`knowledge.md`](knowledge.md).
- **Backend:** Python + FastAPI. It also serves the web page.

Customers can also type a question instead of speaking.

## 1. Create the Azure resources

You need an Azure account. A [free account](https://azure.microsoft.com/free/) includes trial credit.

### Azure Speech (free F0 tier)

1. Go to the [Azure portal](https://portal.azure.com) and choose **Create a resource**.
2. Search for **Speech** and select **Speech** (by Microsoft), then **Create**.
3. Fill in:
   - **Resource group:** create one, e.g. `voice-agent-rg`.
   - **Region:** pick one close to you, e.g. `East US`. Note the short name (e.g. `eastus`).
   - **Name:** any unique name.
   - **Pricing tier:** **Free F0**.
4. Select **Review + create**, then **Create**.
5. When it's ready, open the resource and go to **Keys and Endpoint**. Copy **KEY 1** and the **Location/Region**.

### Azure OpenAI

1. In the Azure portal, **Create a resource** → search **Azure OpenAI** → **Create**.
2. Use the same resource group, choose a region, give it a name, and pick the **Standard S0** tier. Create it.
3. Open the resource, go to **Keys and Endpoint**, and copy **KEY 1** and the **Endpoint** (looks like `https://your-name.openai.azure.com/`).
4. Open **Azure AI Foundry** (button on the resource's overview page), go to **Deployments** → **Deploy model** → **Deploy base model**, pick **gpt-4o-mini** (cheap and fast), and deploy it. Note the **deployment name**.

> Trial credit on a new Azure account typically lasts 30 days. After that, Azure OpenAI is pay-as-you-go. Short answers with gpt-4o-mini cost very little.

## 2. Configure

```bash
cp .env.example .env
```

Open `.env` and fill in the values you copied:

| Variable | Where it comes from |
| --- | --- |
| `AZURE_SPEECH_KEY` | Speech resource → Keys and Endpoint → KEY 1 |
| `AZURE_SPEECH_REGION` | Speech resource region, e.g. `eastus` |
| `AZURE_SPEECH_VOICE` | Optional. Voice for answers, default `en-US-JennyNeural` |
| `AZURE_SPEECH_LANGUAGE` | Optional. Language customers speak, default `en-US` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource → Keys and Endpoint → Endpoint |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI resource → Keys and Endpoint → KEY 1 |
| `AZURE_OPENAI_DEPLOYMENT` | The deployment name you created, e.g. `gpt-4o-mini` |
| `AZURE_OPENAI_API_VERSION` | Optional. Default `2024-10-21` |

`.env` is git-ignored. Never commit it or share your keys.

Then put your business info (hours, prices, FAQs, policies) in [`knowledge.md`](knowledge.md). The agent answers from that file and says it doesn't know when the answer isn't there.

## 3. Run

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open <http://localhost:8000>, allow microphone access, tap the mic and ask a question.

The browser only allows the microphone on `localhost` or over HTTPS, so use HTTPS when you deploy it.

## Tests

```bash
pytest
```

## Project layout

```
app/
  main.py          FastAPI app: speech token, /api/ask, serves the page
  llm.py           Answer generation (Azure OpenAI). Swap this to change LLM.
  static/
    index.html     The page
    app.js         UI logic
    speech.js      Speech layer (Azure Speech). Swap this to change speech provider.
    style.css
knowledge.md       Your business info the agent answers from
.env.example       Template for your keys
```
