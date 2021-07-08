import pandas as pd
import numpy as np
import os
import inflect


def _get_unique_words(list):
    """
    Returns the unique words from a python list.
    :param list: python array of words
    :return: numpy array list
    """
    array = np.array(list)
    return np.unique(array)


def _import_excel(filepath):
    """
    function which imports a tab-delimited csv when given the filepath.
    """
    #Reads data from excel file into pandas dataframe.
    data = pd.read_excel(rf'{filepath}'
                        ,usecols=[0,1], header=0, na_values=['NA'])
    #print(f'This is the original data: {data}')

    series_1 = pd.Series(data.iloc[:,0])
    series_2 = pd.Series(data.iloc[:,1]).dropna()
    #print(f'This is series 1 {series_1}')
    #print(f'This is series 2 {series_2}')
    return series_1, series_2


def _split_by_pattern(dataframe):
    # The character to look for to identify a phrase keyword.
    phrase_splitword = "\""
    exact_splitword = "["

    campaign_keywords = dataframe

    # Finding the entries in broad column concat that start wih " and place them in new series, removing na values from deleted entries.
    phrase = campaign_keywords.where(campaign_keywords.str.startswith(phrase_splitword)).dropna()
    exact = campaign_keywords.where(campaign_keywords.str.startswith(exact_splitword)).dropna()
    # Creating the broad keyword list by finding the entries that are not in the above two series. (with other words, removing the exact and phrase keywords)
    broad = campaign_keywords[~campaign_keywords.isin(phrase)]
    # For the final bit unnecessary whitespaces as well as the quotation marks and square brackets are removed.
    broad = broad[~broad.isin(exact)].reset_index(drop=True).str.strip().str.lower()
    # Remove the quotations on both sides.
    phrase = phrase.str.replace('"', '').str.strip().str.lower()
    # Remove square brackets on both sides.
    exact = exact.str.strip('[]').str.strip().str.lower()
    # at this point you have broad, phrase, exact containing all the keywords with different match types for the campaign.

    return broad, phrase, exact


def _remove_words(series_1, series_2):

    #array_br_ph_ex is an array containing 3 series where br is abbreviation for terms
    #that are broad, ph for phrases and ex for exact.
    #The arrays are in the order specified by the array name (Broad_Series, Phrase_Series, Exact_Series)
    array_br_ph_ex = _split_by_pattern(series_2)

    broad_words = array_br_ph_ex[0]
    phrase_words = array_br_ph_ex[1]
    exact_words = array_br_ph_ex[2]

    found_words = pd.Series(dtype=object)
    #Make all words lowercase, if this is not done cat would not match with Cat when searching.
    series_1.str.lower()
    for i in range(len(array_br_ph_ex)):
        if i == 0:
            #Broad search
            for value in broad_words.items():
                #value is a tuple containing index and then the word in series_2.
                pattern_word = str(value[1])
                #split the sentence/word into components ie. shoe cabinet would become an array = [shoe, cabinet] whereas shoe would only become = [shoe]
                split_word = pattern_word.split()
                for i in range(len(split_word)):
                    #for each word in the array check if it exist in series_1.
                    word = split_word[i]
                    found_words = found_words.append(series_1.where(series_1.str.contains(fr"\b{word}\b")))
                    found_words = found_words.dropna()
        if i == 1:
            #Phrase search
            for value in phrase_words.items():
                pattern_word = str(value[1])
                found_words = found_words.append(series_1.where(series_1.str.contains(fr"\b{pattern_word}\b")))
                found_words = found_words.dropna()
        if i == 2:
            #Exact search
            for value in exact_words.items():
                pattern_word = str(value[1])
                found_words = found_words.append(series_1.where(series_1.str.fullmatch(pattern_word)))
                found_words = found_words.dropna()

    found_words.drop_duplicates().reset_index(drop=True)
    output = series_1[~series_1.isin(found_words)].reset_index(drop=True)


    return output


def _search_phrase(series_1, search_term):
    search_term = str(search_term).lower()
    series_1 = pd.Series(series_1, dtype=object)
    new_series = pd.Series(dtype=object)
    words_found = pd.Series(dtype=object)
    output = []
    # \b   \b is regex syntax for word boundaries to make sure exactly that word is searched for.
    words_found = words_found.append(series_1.where(series_1.str.contains(fr"\b{search_term}\b"))).dropna().reset_index(drop=True)
    #new_series gets populated with the remainder of the term once the search term has been removed.
    new_series = words_found.str.split(f'{search_term}')
    for value in new_series.items():
        #because split has created an array of arrays of terms before and after the search term
        #we cycle through all of them and append to an output array.
        array = value[1]
        #value[0] is just the index so we only look at value[1]
        array_val1 = array[0]
        array_val2 = array[1]
        if array_val1:
            array_val1 = array_val1.strip()
            #If there was a word before the search term, append it to ouput array.
            output.append(array_val1)
        if array_val2:
            array_val2 = array_val2.strip()
            #if there was a word after the search term, append it to output array.
            output.append(array_val2)


    words_found.dropna()

    out1 = pd.Series(output, name='Output')
    out2 = pd.Series(words_found, name='Containing Search word')
    #dataframe_output = pd.concat([out1,out2], axis=1)


    return out1,out2

def _make_plural_singular(search_word, searched_terms):

    p = inflect.engine()
    searched_terms.append(f'"{search_word}"')

    if p.singular_noun(search_word) != False:
        # singular_noun returns false if singular noun is detected.

        singular_word = p.singular_noun(search_word)
        searched_terms.append(f'"{singular_word}"')
    else:
        # if it is not singular, make it plural and add to list.
        plural_word = p.plural(search_word)
        searched_terms.append(f'"{plural_word}"')

    return searched_terms



if __name__ == "__main__":

    current_directory = os.getcwd()
    filepath = os.path.join(current_directory, 'uploads', 'list_examples.xlsx')
    data = _import_excel(filepath)

    result = _remove_words(data[0], data[1])
    new_list = _search_phrase(result[0], "shoe cupboard")
    new_list2 = _search_phrase(result[0], "Oak Shoe Storage")
    new_list3 = _search_phrase(result[0], "Shoe Storage Cabinet")

    search_term = "rabbit hutch"
    search_term2 = "kitchen knife"
    search_term3 = "shoe storage cabinet"
    p = inflect.engine()
    plural = p.plural(search_term)

    print(plural)
    print(p.plural(search_term2))
    print(p.plural(search_term3))

    #print(out1)
    #out2 = pd.Series(result[1], name='Removed Words')
    #dataframe_output = pd.concat([out1,out2], axis=1)
    #print(dataframe_output)

    dataframe_output = pd.concat([new_list,new_list2,new_list3], axis=1)
    #dataframe_output.to_excel('new_filename7.xlsx')

