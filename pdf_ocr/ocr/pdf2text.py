# -*- coding: utf-8 -*-
"""
pdf2text.py - convert pdf files to text files using OCR
Copied without shame from https://huggingface.co/spaces/pszemraj/document-summarization/tree/main
"""
import logging
import os
import re
import shutil
import time
import torch
from datetime import date
from os.path import basename, dirname, join
from pathlib import Path

os.environ["USE_TORCH"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S",
)


from cleantext import clean
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from spellchecker import SpellChecker


def simple_rename(filepath, target_ext=".txt"):
    """simple_rename - get a new str to rename a file"""
    _fp = Path(filepath)
    basename = _fp.stem
    return f"OCR_{basename}_{target_ext}"


def rm_local_text_files(name_contains="RESULT_"):
    """
    rm_local_text_files - remove local text files
    """
    files = [f for f in Path.cwd().iterdir() if f.is_file() and f.suffix == ".txt" and name_contains in f.name]
    logging.info(f"removing {len(files)} text files")
    for f in files:
        os.remove(f)
    logging.info("done")


def corr(
    s: str,
    add_space_when_numerics=False,
    exceptions=["e.g.", "i.e.", "etc.", "cf.", "vs.", "p."],
) -> str:
    """corrects spacing in a string
    Args:
        s (str): the string to correct
        add_space_when_numerics (bool, optional): [add a space when a period is between two numbers, example 5.73]. Defaults to False.
        exceptions (list, optional): [do not change these substrings]. Defaults to ['e.g.', 'i.e.', 'etc.', 'cf.', 'vs.', 'p.'].
    Returns:
        str: the corrected string
    """
    if add_space_when_numerics:
        s = re.sub(r"(\d)\.(\d)", r"\1. \2", s)

    s = re.sub(r"\s+", " ", s)
    s = re.sub(r'\s([?.!"](?:\s|$))', r"\1", s)

    # fix space before apostrophe
    s = re.sub(r"\s\'", r"'", s)
    # fix space after apostrophe
    s = re.sub(r"'\s", r"'", s)
    # fix space before comma
    s = re.sub(r"\s,", r",", s)

    for e in exceptions:
        expected_sub = re.sub(r"\s", "", e)
        s = s.replace(expected_sub, e)

    return s


def fix_punct_spaces(string: str) -> str:
    """
    fix_punct_spaces - fix spaces around punctuation
    :param str string: input string
    :return str: string with spaces fixed
    """

    fix_spaces = re.compile(r"\s*([?!.,]+(?:\s+[?!.,]+)*)\s*")
    string = fix_spaces.sub(lambda x: "{} ".format(x.group(1).replace(" ", "")), string)
    string = string.replace(" ' ", "'")
    string = string.replace(' " ', '"')
    return string.strip()


def clean_OCR(ugly_text: str) -> str:
    """
    clean_OCR - clean up the OCR text
    :param str ugly_text: input text to be cleaned
    :return str: cleaned text
    """
    # Remove all the newlines.
    cleaned_text = ugly_text.replace("\n", " ")
    # Remove all the tabs.
    cleaned_text = cleaned_text.replace("\t", " ")
    # Remove all the double spaces.
    cleaned_text = cleaned_text.replace("  ", " ")
    # Remove all the spaces at the beginning of the text.
    cleaned_text = cleaned_text.lstrip()
    # remove all instances of "- " and " - "
    cleaned_text = cleaned_text.replace("- ", "")
    cleaned_text = cleaned_text.replace(" -", "")
    return fix_punct_spaces(cleaned_text)


def move2completed(from_dir, filename, new_folder: str = "completed", verbose: bool = False):
    """
    move2completed - move a file to a new folder
    """
    old_filepath = join(from_dir, filename)

    new_filedirectory = join(from_dir, new_folder)

    if not os.path.isdir(new_filedirectory):
        os.mkdir(new_filedirectory)
        if verbose:
            print("created new directory for files at: \n", new_filedirectory)
    new_filepath = join(new_filedirectory, filename)

    try:
        shutil.move(old_filepath, new_filepath)
        logging.info("successfully moved the file {} to */completed.".format(filename))
    except:
        logging.info("ERROR! unable to move file to \n{}. Please investigate".format(new_filepath))


custom_replace_list = {
    "t0": "to",
    "'$": "'s",
    ",,": ", ",
    "_ ": " ",
    " '": "'",
}

replace_corr_exceptions = {
    "i. e.": "i.e.",
    "e. g.": "e.g.",
    "e. g": "e.g.",
    " ,": ",",
}


spell = SpellChecker()


def check_word_spelling(word: str) -> bool:
    """
    check_word_spelling - check the spelling of a word
    Args:
        word (str): word to check
    Returns:
        bool: True if word is spelled correctly, False if not
    """

    misspelled = spell.unknown([word])

    return len(misspelled) == 0


def eval_and_replace(text: str, match_token: str = "- ") -> str:
    """
    eval_and_replace  - conditionally replace all instances of a substring in
    a string based on whether the eliminated substring results in a valid word
    Args:
        text (str): text to evaluate
        match_token (str, optional): token to replace. Defaults to "- ".
    Returns:
        str:  text with replaced tokens
    """

    if match_token not in text:
        return text
    else:
        while True:
            full_before_text = text.split(match_token, maxsplit=1)[0]
            full_before_text_split = full_before_text.split()
            full_before_split_suffix = full_before_text_split[0] if full_before_text_split else ""
            before_text = [char for char in full_before_split_suffix if char.isalpha()]
            before_text = "".join(before_text)
            full_after_text = text.split(match_token, maxsplit=1)[-1]
            after_text = [char for char in full_after_text.split()[0] if char.isalpha()]
            after_text = "".join(after_text)
            full_text = before_text + after_text
            if check_word_spelling(full_text):
                text = full_before_text + full_after_text
            else:
                text = full_before_text + " " + full_after_text
            if match_token not in text:
                break
        return text


def cleantxt_ocr(ugly_text, lower=False, lang: str = "en") -> str:
    """
    cleantxt_ocr - clean text from OCR
        https://pypi.org/project/clean-text/
    Args:
        ugly_text (str): text to clean
        lower (bool, optional): lowercase text. Defaults to False.
        lang (str, optional): language of text. Defaults to "en".
    Returns:
        str: cleaned text
    """

    cleaned_text = clean(
        ugly_text,
        fix_unicode=True,  # fix various unicode errors
        to_ascii=True,  # transliterate to closest ASCII representation
        lower=lower,  # lowercase text
        no_line_breaks=True,  # fully strip line breaks as opposed to only normalizing them
        no_urls=True,  # replace all URLs with a special token
        no_emails=True,  # replace all email addresses with a special token
        no_phone_numbers=True,  # replace all phone numbers with a special token
        no_numbers=False,  # replace all numbers with a special token
        no_digits=False,  # replace all digits with a special token
        no_currency_symbols=False,  # replace all currency symbols with a special token
        no_punct=False,  # remove punctuations
        replace_with_punct="",  # instead of removing punctuations you may replace them
        replace_with_url="this url",
        replace_with_email="this email",
        replace_with_phone_number="this phone number",
        lang=lang,  # set to 'de' for German special handling
    )

    return cleaned_text


def format_ocr_out(OCR_data):
    """format OCR output to text"""
    if isinstance(OCR_data, list):
        text = " ".join(OCR_data)
    else:
        text = str(OCR_data)
    _clean = cleantxt_ocr(text)
    return corr(_clean)


def postprocess(text: str) -> str:
    """to be used after recombining the lines"""

    proc = corr(cleantxt_ocr(text))

    for k, v in custom_replace_list.items():
        proc = proc.replace(str(k), str(v))

    proc = corr(proc)

    for k, v in replace_corr_exceptions.items():
        proc = proc.replace(str(k), str(v))

    return eval_and_replace(proc)


def result2text(result, as_text=False) -> str or list:
    """Convert OCR result to text"""

    full_doc = []
    for i, page in enumerate(result.pages, start=1):
        text = ""
        for block in page.blocks:
            text += "\n\t"
            for line in block.lines:
                for word in line.words:
                    # print(dir(word))
                    text += word.value + " "
        full_doc.append(text)

    return "\n".join(full_doc) if as_text else full_doc


def convert_PDF_to_Text(
    PDF_file,
    ocr_model=None,
    max_pages: int = 20,
) -> str:
    """
    convert_PDF_to_Text - convert a PDF file to text
    :param str PDF_file: path to PDF file
    :param ocr_model: model to use for OCR, defaults to None (uses the default model)
    :param int max_pages: maximum number of pages to process, defaults to 20
    :return str: text from PDF
    """
    st = time.perf_counter()
    PDF_file = Path(PDF_file)
    ocr_model = ocr_predictor(pretrained=True) if ocr_model is None else ocr_model
    logging.info(f"starting OCR on {PDF_file.name}")
    doc = DocumentFile.from_pdf(PDF_file)
    truncated = False
    if len(doc) > max_pages:
        logging.warning(f"PDF has {len(doc)} pages, which is more than {max_pages}.. truncating")
        doc = doc[:max_pages]
        truncated = True

    # Analyze
    logging.info(f"running OCR on {len(doc)} pages")
    result = ocr_model(doc)
    raw_text = result2text(result)
    proc_text = [format_ocr_out(r) for r in raw_text]
    fin_text = [postprocess(t) for t in proc_text]

    ocr_results = "\n\n".join(fin_text)

    fn_rt = time.perf_counter() - st

    logging.info("OCR complete")

    results_dict = {
        "num_pages": len(doc),
        "runtime": round(fn_rt, 2),
        "date": str(date.today()),
        "converted_text": ocr_results,
        "truncated": truncated,
        "length": len(ocr_results),
    }

    return results_dict


def main():
    ocr_model = ocr_predictor(
        "db_resnet50",
        "crnn_mobilenet_v3_large",
        pretrained=True,
        assume_straight_pages=True,
    )
    ocr_model = ocr_model.to(torch.device("cuda:0"))

    r = convert_PDF_to_Text("news.pdf", ocr_model=ocr_model)
    print(f"{r}")
    r = convert_PDF_to_Text("scan-chirilic.pdf", ocr_model=ocr_model)
    print(f"{r}")
    r = convert_PDF_to_Text("broke.pdf", ocr_model=ocr_model)
    print(f"{r}")


if __name__ == "__main__":
    main()
