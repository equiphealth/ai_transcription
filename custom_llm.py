import os
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

class CustomLLM(BaseModel):
    """
    Custom LLM input parameter data types.
    """
    model: str
    temperature: float = 0.3

    class Config:
        arbitary_types_allowed = False

    def generate(self, messages):
        """
        Generates a response based on a given transcript and template using a specified language model.

        Parameters:
        transcript (str): The text of the transcript to be processed.
        prompt (str): Initial text prompt input.
        working_example (str): Used to tell ChatGPT what the output should look like ("few-shot-learning")

        Returns:
        tuple: A tuple containing the generated response as a string and the updated list of messages.
        """
        # Load the OpenAI API key and set the uptrain model key
        load_dotenv()
        client = OpenAI(api_key=os.environ['OPENAI_API_PATIENT_INSIGHT_KEY'])
        os.environ["OPENAI_API_KEY"] = os.environ['OPENAI_API_UPTRAIN_KEY']

        # Call the LLM API
        completion = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature
        )
        response = completion.choices[0].message.content
        return response