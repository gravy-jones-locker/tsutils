# This is a storage of common and useful functions that may be used in many scripts.
# Last updated: 21.07.2020
import traceback
import pandas as pd
import csv
import re

from json import loads


def excel_to_df_dict(filename: str, separator: str = ',') -> dict:
    """
    This function transforms CSV or Excel (xlsx) file into a dictionary with Pandas DataFrame object(s).

    :param filename: a string with the name of input file. F.e, "input.csv" or "report.xlsx".
    :param separator: delimiter between columns in CSV file (coma by default). Works only with CSV.
    :return: a dict object, where keys are names of tabs (a tab if it's a CSV file). Values are pd.DataFrame objects.
    """
    df_dict = dict()
    if '.xlsx' in filename:
        xl = pd.ExcelFile(filename)  # Create Pandas Excel file.
        tables_names = list(xl.sheet_names)
        for tab_name in tables_names:
            df_dict[tab_name] = xl.parse(tab_name)  # parse names of tabs.
    elif '.csv' in filename:
        table = pd.read_csv(filename, encoding='utf8', delimiter=separator)  # Pandas Excel file.
        df_dict['csv'] = table
    else:
        raise OSError.filename(f"file with name {filename} contains neither .csv nor .xlsx it its name.")

    return df_dict


def file_to_row(filename: str, encoding: str = 'utf8') -> str:
    """
    This function reads the first row of the file and returns it.

    :param filename: a name of the file to read.
    :param encoding:  encoding to use while reading the file.
    :return: it returns the first line of the file as a str object.
    """
    file = open(filename, encoding=encoding)
    string = file.readline()
    file.close()
    string = string.strip()

    return string


def run_main_func(main_func, printing_function=print) -> bool:
    """
    This function accepts the main function of a script and works as a comfortable "wrapper". In case of an error, this
    wrapper will inform user of error and won't close compiled exe file or a python console immediately.

    :param main_func: the main function of a script.
    :param printing_function: a function to print data. Default to print(). Other functions can be used.
    :return: the function returns boolean True if the main_func has run successfully. False otherwise.
    """
    try:
        main_func()
        return True
    except:
        error_message = traceback.format_exc()
        printing_function('*' * 20 + ' E R R O R ' + '*' * 20)
        printing_function('Error message:')
        printing_function(error_message)
        printing_function('*' * 51)
        return False


def create_csv_file(filename: str, header: list = None, encoding: str = 'utf-8', delimiter: str = ','):
    """
    This function creates an empty csv file and returns python file object and a writer from "csv" library. So that
    after the call of the function you can use the writer to write new data to the file. Writer accepts a list or
    lists of strings to write it down to csv_file.

    :param filename: a name of the csv file with type str. Should have ".csv" at the end of it.
    :param header: a list with columns' names. List of strings.
    :param encoding: encoding of csv_file.
    :param delimiter: a separator between columns for the CSV file.
    :return: csv_file and writer for it.
    """
    csv_file = open(filename, 'w', newline="", encoding=encoding)
    if encoding in ['utf8', 'utf-8']:
        csv_file.write('\ufeff')  # Needed for reading the file as  utf-8
    writer = csv.writer(csv_file, delimiter=delimiter)
    if bool(header) is True:
        writer.writerow(header)

    return csv_file, writer


def tokenize_string(string: str, to_lower: bool = True, del_apostrophe: bool = True, min_token_len: int = 0) -> list:
    """
    This function splits a string into lowercased words. It also deletes punctuation marks, leaving words and numbers.
    Python re library is used to delete punctuation marks. Also, it delete's ending 's.

    :param string: str object variable to be tokenized.
    :param to_lower: should a string be lowercased while processingor not.
    :param del_apostrophe: erase apostrophe and 's ending from tokens.
    :param min_token_len: the minimum length of a token. Defaults to 0.
    :return: a list with tokens (words).
    """
    if to_lower:
        string = string.lower()
    tokens = string.split()
    tokens = [re.sub('[.:,!?\"]', '', word) for word in tokens]  # delete punctuation.
    if del_apostrophe is True:
        endings_func = lambda token: token[:-2] if token[-2:] == '’s' or token[-2:] == "'s" else token
        tokens = [endings_func(token) for token in tokens]  # delete 's ending.
        tokens = [endings_func(token) for token in tokens]  # delete 's ending.
        tokens = [re.sub("'", '', word) for word in tokens]  # delete '.
    tokens = list(filter(None, tokens))  # delete empty "" tokens.
    tokens = [token for token in tokens if bool(re.search('\w', token)) is True]
    tokens = [token for token in tokens if len(token) >= min_token_len]
    tokens = [token[1:] if bool(re.findall('\W', token[0])) else token for token in tokens]
    tokens = [token[:-1] if bool(re.findall('\W', token[-1])) else token for token in tokens]

    return tokens


def tokenize_url(url: str) -> list:
    """
    This function splits a URL string into lowercased words. Also deletes punctuation marks, leaving words and numbers.
    Also deletes parameters from a URL.

    :param url: str object (URL like) variable to be tokenized.
    :return: a list with tokens (words).
    """
    url_tokens = url.split('/')
    url_string = ' '.join(url_tokens)
    url_tokens = url_string.split('-')
    url_string = ' '.join(url_tokens)
    url_string = re.sub('https:', '', url_string)
    url_string = re.sub('http:', '', url_string)
    url_string = re.sub('www', '', url_string)
    url_string = url_string.strip()
    url_string = url_string.split('.')
    url_string = ' '.join(url_string)
    url_string = url_string.lower()
    url_tokens = url_string.split(' ')
    url_tokens = list(filter(None, url_tokens))  # delete empty "" tokens.
    if '?' in url_tokens[-1]:
        url_tokens[-1] = url_tokens[-1][:url_tokens[-1].find('?')]

    return url_tokens


def file_to_list(filename: str, encoding: str = 'utf8') -> list:
    """
    This function reads a file and converts its rows to Python list. One row -> one element with str type in a list.

    :param filename: a file with text in its rows.
    :param encoding: encoding of the filename. Default to utf8.
    :return: Python list object where one element is one row from an input file. Each element has type str.
    """
    file = open(filename, 'r', encoding=encoding)
    rows_list = [row.strip() for row in file]
    file.close()

    return rows_list


def create_output_name(initial_name: str, ending: str = '') -> str:
    """
    This function transforms a file name by adding between its name and extension ending string.

    :param initial_name: the original name of the file.
    :param ending: what should be added between the name itself and an extension of the file.
    :return: processed string.
    """
    name_parts = initial_name.split('.')
    if len(name_parts) == 1:
        final_name = initial_name + ending
    elif len(name_parts) > 1:
        final_name = ''.join(name_parts[:-1]) + ending + '.' + name_parts[-1]
    else:
        final_name = 'output' + '_' + ending

    return final_name


def between_markers(text: str, begin: str, end: str) -> str:
    """
    Returns a substring between 2 elements in a string.
    :param text: src text.
    :param begin: beginning of a substring.
    :param end: ending of a substirng.
    :return: a substring.
    """
    start = text.find(begin) + len(begin) if begin in text else None
    stop = text[start:].find(end) if end in text else None
    return text[start:start+stop]


def df_to_rows(df: pd.DataFrame, rows_limit: int = None) -> list:
    """
    This function takes first rows_limit rows from an input df and pack it into a list.

    :param df: a dataframe with elements or pairs of elements from URLs.
    :param rows_limit: how many first rows to include in the output list.
    :return: a list of lists: [[col1,col2], [col1,col2]]. Each outer element is a row, each inner - column value.
    """
    rows = df.to_dict(orient='split')['data']
    if rows_limit is not None:
        rows = rows[:rows_limit]

    return rows


def filter_dict_keys(dictionary: dict, keys_required: list, filter_none: bool = False):
    """
    This function leaves only some keys in a dictionary and returns it.

    :param dictionary: input dictionaries.
    :param keys_required: keys that should only be present in a dictionary.
    :param filter_none: delete keys, which values are not True.
    :return: filtered dictionary.
    """
    filtered_dict = dictionary.copy()
    for key, value in dictionary.items():
        if key not in keys_required:
            del filtered_dict[key]
        elif filter_none is True and bool(value) is False:
            del filtered_dict[key]

    return filtered_dict


def rows_to_df(rows: [list, tuple], header: list) -> pd.DataFrame:
    """
    This function transforms rows with column values to a pandas.DataFrame object.

    :param rows: an array where each item represents a row. Item contains values that corresponds to the header.
    :param header: a list with the table columns.
    :return: a pandas.DataFrame table with all the input data.
    """
    table = pd.DataFrame()
    np_rows = np.array(rows)

    for idx in range(len(header)):
        table[header[idx]] = np_rows[:, idx]

    return table


def read_table(table_path: str, sep: str = ',', fill_na: bool = True) -> pd.DataFrame:
    """
    This function reads local CSV or Excel table from a file and returns Pandas table.

    :param table_path: a path to a file with a CSV or Excel table.
    :param sep: only used for CSV files. Stands for the symbol that separates columns in a line.
    :param fill_na: if True, all the empty cells will be replaced with "". Otherwise, Pandas nan value will be used.
    :return: pandas.DataFrame object.
    """
    if table_path.endswith('.csv'):
        input_df = pd.read_csv(table_path, sep=sep, encoding='utf8', low_memory=False)
    elif table_path.endswith('.xlsx'):
        input_df = pd.read_excel(table_path)
    else:
        ValueError(f"The file you are trying to read ({table_path}) is not CSV either Excel format.")
    if fill_na:
        input_df = input_df.fillna('')

    return input_df


def string_to_tokens(string: str, min_token_len: int = 1) -> list:
    """
    This function can divide string into tokens starting from a certain length. For example, string "best friend, which"
    may be divided into ["be", "es", "st",...."bes", "est", "stf", ... "best", "estf", "stfr", ..., etc.].
    :param string: a string with text to divide by tokens.
    :param min_token_len: min length of a token.
    :return: a list with strings, where one string is a token. The last token is always the whole input string.
    """
    string = ''.join(re.findall('\w', string))
    string_len = len(string)
    if min_token_len > string_len:
        return []
    elif min_token_len == string_len:
        return [string]

    tokens = []
    for word_length in range(min_token_len, string_len):
        for letter_idx in range(string_len):
            if letter_idx + word_length > string_len:
                break
            token = string[letter_idx: letter_idx+word_length]
            tokens.append(token)

    tokens.append(string)
    return tokens


def create_batches(initial_items: [list, set], max_size: int) -> list:
    """
    Create batches of items from initial set/list of items according to the max size.

    :param initial_items: a list or set with items of any type.
    :param max_size: max size of one batch. If initial_items % max_size !=0, the the last batch will contain
                    < max_size items.
    :return: a list with lists with items: [[item1, item2], [item3,item4], ...]
    """
    batches = []
    for start in range(0, len(initial_items), max_size):
        finish = start + max_size
        curr_batch = initial_items[start: finish]
        batches.append(curr_batch)

    return batches


def url_to_domain(url: str) -> str:
    """
    A function to parse a domain (together with subdomains) from a URL.
    :param url: string with a URL.
    :return: a string with a domain.
    """
    if url.startswith('https'):
        url = url[8:]
    elif url.startswith('http'):
        url = url[7:]
    domain = url[:url.find('/')]
    if domain.startswith('www.'):
        domain = domain[4:]

    return domain


def slugify(text: str, lowercase: bool = False, connector: str = '_') -> str:
    """
    Create a slug from an input string.

    :param text: str object, a text to create a slug from.
    :param lowercase: boolean, if True - transform a slug to lowercased letters. False - don't do it.
    :param connector: str object, a symbol to join slug parts with.
    :return: str object, a string with text.
    """
    parts = text.split()
    parts = [''.join(re.findall('\w', part)) for part in parts]
    slug = connector.join(parts)
    if lowercase:
        slug = slug.lower()

    return slug