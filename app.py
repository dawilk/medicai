import gradio as gr
import json
import os
import requests

GRADIO_SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "localhost") # default is localhost, but docker needs to be set to "0.0.0.0"
GRADIO_SERVER_PORT = int(os.getenv("GRADIO_SERVER_PORT", 7860))

# Set the API URL from ENV OLLAMA_API_URL
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
MODEL=os.getenv("MODEL", "health")  # default is health, but can be set to any other model

def print_like_dislike(x: gr.LikeData):
    print(x.index, x.value, x.liked)


def add_message(history, message):
    for x in message["files"]:
        history.append({"role": "user", "content": {"path": x}})
    if message["text"] is not None:
        history.append({"role": "user", "content": message["text"]})
    return history, gr.MultimodalTextbox(value=None, interactive=False)

def get_system_prompt(settings):
    """
    Generate a system prompt based on the user's settings.
    """

    system_prompt = "The following are the user's personal settings:\n"
    for key, value in settings.items():
        system_prompt += f"- {key}: {value}\n"
    system_prompt += "\nUse this information to provide more personalized responses."
    # print("System prompt:", system_prompt)  # Debugging output
    return system_prompt

def llm(messages, system_prompt=""):
    """
    Sends the conversation history and system prompt to the Ollama API and streams the response.
    """

    # Add the user message to the conversation history
    # print("History sent to Ollama:", messages)
    r = requests.post(
        f'{OLLAMA_API_URL}',
        json={
            'model': MODEL,
            'messages': messages,
        },
        stream=True  # Enable streaming
    )
    r.raise_for_status()

    for line in r.iter_lines():
        if line.strip():  # Ensure the line is not empty
            body = json.loads(line)
            if 'error' in body:
                raise Exception(body['error'])

            response_part = body.get('message', {}).get('content', '')
            yield response_part  # Yield each part of the response as it arrives

            if body.get('done', False):
                break

def bot(history: list):
    """
    Updates the conversation history and streams the assistant's response.
    """
    global current_settings
    system_prompt = get_system_prompt(current_settings)

    # Add the system prompt to the conversation history
    if system_prompt:
        history.append({"role": "system", "content": system_prompt})
    history.append({"role": "assistant", "content": ""})

    # Add the [system prompt and] user message to the conversation history
    for response_part in llm(history, system_prompt):
        # Drop the system prompt before updating the UI
        if history[-2]["role"] == "system":
            history.pop(-2)

        history[-1]["content"] += response_part
        yield history  # Yield the updated history to stream updates to the UI

with gr.Blocks() as medicAI:
    gr.Markdown(
        """
        <h1><center>medicAI</center></h1>
        <p style="text-align: center;">Your personal healthcare assistant powered by AI.</p>
        """
    )

    chatbot = gr.Chatbot(
        elem_id="chatbot",
        type="messages",
        show_label=False,
    )

    chat_input = gr.MultimodalTextbox(
        interactive=True,
        file_count="multiple",
        placeholder="Enter message...",
        show_label=False,
        sources=[],
        # sources=["microphone", "upload"], # disabled additional sources for now
    )

    # Global variable to store current settings for use in the system prompts
    # Only modified settings are included in the system prompt
    global current_settings
    current_settings = {}

    # Function to update the settings dictionary
    def update_settings(key, value):
        current_settings[key] = value
        # print(f"Updated settings: {current_settings}")  # Debugging output

    # Define the settings dynamically
    settings_config = [
        {"type": gr.Number, "label": "Age", "info": "Enter your age."},
        {"type": gr.Radio, "label": "Sex", "info": "Select your sex.", "choices": [None, "Male", "Female", "Other"]},
        {"type": gr.Radio, "label": "Race", "info": "Select your race.", "choices": [None, "White", "Black", "Asian", "Hispanic", "Other"]},
        {"type": gr.Number, "label": "Weight (lbs)", "info": "Enter your weight in lbs."},
        {"type": gr.Number, "label": "Height (inches)", "info": "Enter your height in inches."},
        {"type": gr.Textbox, "label": "Allergies", "info": "List any allergies you have.", "placeholder": "e.g., Penicillin, Nuts"},
        {"type": gr.Textbox, "label": "Medications", "info": "List any medications you are currently taking.", "placeholder": "e.g., Aspirin, Metformin"},
        {"type": gr.Textbox, "label": "Medical History", "info": "Provide any relevant medical history.", "placeholder": "e.g., Diabetes, Hypertension"},
        {"type": gr.Textbox, "label": "Family History", "info": "Provide any relevant family medical history.", "placeholder": "e.g., Heart disease, Cancer"},
        {"type": gr.Textbox, "label": "Lifestyle", "info": "Describe your lifestyle (e.g., diet, exercise).", "placeholder": "e.g., Vegetarian, Sedentary"},
        {"type": gr.Radio, "label": "Smoking", "info": "Do you smoke?", "choices": [None, "Yes", "No"]},
        {"type": gr.Radio, "label": "Alcohol Consumption", "info": "Do you consume alcohol?", "choices": [None, "Yes", "No"]},
        {"type": gr.Radio, "label": "Exercise", "info": "Do you exercise regularly?", "choices": [None, "Yes", "No"]},
        {"type": gr.Radio, "label": "Sleep Quality", "info": "Describe sleep quality", "choices": [None, "Good", "Poor"]},
        {"type": gr.Radio, "label": "Stress", "info": "Do you experience high stress levels?", "choices": [None, "Yes", "No"]},
        {"type": gr.Radio, "label": "Diet", "info": "How would you describe your diet?", "choices": [None, "Healthy", "Unhealthy"]},
    ]

    # Dynamically create the settings components
    with gr.Accordion(
        "Personal Settings",
        open=False,
        elem_id="settings",
        visible=True,
        ):
        gr.Markdown("<p>Configure your information to help the AI give better responses.</p>")
        with gr.Row():
            for setting in settings_config:
                component_type = setting["type"]
                label = setting["label"]
                info = setting["info"]
                kwargs = {k: v for k, v in setting.items() if k not in ["type", "label", "info"]}

                # Create the component dynamically
                component = component_type(label=label, info=info, **kwargs)

                # Attach a change event to update the settings dictionary
                component.change(lambda val, key=label: update_settings(key, val), inputs=component)

    chat_msg = chat_input.submit(
        add_message, [chatbot, chat_input], [chatbot, chat_input]
    )

    bot_msg = chat_msg.then(bot, chatbot, chatbot, api_name="bot_response")
    bot_msg.then(lambda: gr.MultimodalTextbox(interactive=True), None, [chat_input])


medicAI.title = "medicAI"
medicAI.description = "Your personal healthcare assistant powered by AI."
medicAI.launch(server_name=GRADIO_SERVER_NAME, server_port=GRADIO_SERVER_PORT)
