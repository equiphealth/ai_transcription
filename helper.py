import os
import yaml
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerRegistry

class Helper():
    def __init__(self):
        return self

    @staticmethod
    def load_yaml_to_dict(file_path):
        try:
            with open(file_path, 'r') as file:
                data = yaml.safe_load(file)
            return data
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            return None
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            return None
    @staticmethod
    def read_files_in_folder(folder_path: str) -> list[str]:
        """
        folder_path: folder path to read the transcript files.
        """
        file_contents = []

        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)

            if os.path.isfile(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                    file_contents.append(content)

        return file_contents

    @staticmethod
    def read_file(folder_path: str, file_path: str) -> str:
        """
        file_path: file path to read the transcript files without looping
        """

        # if os.path.isfile(file_path):
        with open(folder_path + "/" + file_path, "r", encoding="utf-8-sig") as f:
            file_contents = f.read()
        return file_contents
    @staticmethod
    def parse_full_name(full_name: str) -> tuple[str, str]:
        """
        Splits a full name into first and last name components.

        Parameters:
        full_name (str): A string representing the full name, e.g., 'Kevin Choi'.

        Returns:
        tuple: A tuple containing the first name and last name as strings.
        """
        # Split the full name by spaces
        name_parts = full_name.split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:])
        elif len(name_parts) == 3:
            # Consider a chosen name or middle name
            first_name = name_parts[0]
            chosen_name = name_parts[1]
            last_name = name_parts[2]
            return [first_name, chosen_name, last_name]
        elif len(name_parts) == 1:
            # If only one part is present, consider it as the first name, and leave the last name empty
            first_name = name_parts[0]
            last_name = ""
        else:
            first_name = ""
            last_name = ""
        return [first_name, last_name]

    @staticmethod
    def scrub(text, fn, cn, ln) -> str:
        """
        Anonymizes sensitive information in the provided text by identifying and replacing personal identifiers.

        Parameters:
        text (str): The text to be anonymized, potentially containing sensitive information.
        fn (str): The first name to be recognized and anonymized in the text.
        cn (str): The chosen name or nickname to be recognized and anonymized in the text. If None, it defaults to an empty string.
        ln (str): The last name to be recognized and anonymized in the text.

        Returns:
        str: The anonymized text with personal identifiers replaced.
        """
        anonymizer = AnonymizerEngine()
        analyzer = AnalyzerEngine()
        registry = RecognizerRegistry()

        if cn == None:
            cn = ''

        first_name = Pattern(
            name='first_name',
            regex=f'\W*((?i){fn})\W*',
            score=1)
        fn_rec = PatternRecognizer(supported_entity='FIRST_NAME', patterns=[first_name])

        chosen_name = Pattern(
            name='chosen_name',
            regex=f'\W*((?i){cn})\W*',
            score=1)
        cn_rec = PatternRecognizer(supported_entity='CHOSEN_NAME', patterns=[chosen_name])

        last_name = Pattern(
            name='last_name',
            regex=f'\W*((?i){ln})\W*',
            score=1)
        ln_rec = PatternRecognizer(supported_entity='LAST_NAME', patterns=[last_name])

        dob = Pattern(
            name='dob',
            regex='(?i)DOB.+?(\d{1,2}\s?\/\d{1,2}\s?\/\d{2,4})|(\d{1,2})\s*(?i)yo?',
            score=1)
        dob_rec = PatternRecognizer(supported_entity='DOB/AGE', patterns=[dob])
        # analyzer = AnalyzerEngine()
        analyzer.registry.add_recognizer(fn_rec)
        # analyzer.registry.add_recognizer(cn_rec)
        analyzer.registry.add_recognizer(ln_rec)
        # analyzer.registry.add_recognizer(dob_rec)
        analyzer_results = analyzer.analyze(text=text, language='en', entities=["FIRST_NAME",
                                                                                "CHOSEN_NAME",
                                                                                "LAST_NAME",
                                                                                "DOB/AGE",
                                                                                "LOCATION"])

        anonymizer_request = anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results
        )
        return anonymizer_request.text