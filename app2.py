from flask import Flask, render_template, redirect, request, url_for, session, send_file
from flask_session.__init__ import Session
from flask_wtf import FlaskForm
from wtforms import SubmitField
from flask_wtf.file import FileField, FileAllowed, FileRequired
import pandas as pd
from wtforms.validators import InputRequired
import os
import uuid
import inflect
import pandas as pd
from indataframe import _remove_words, _import_excel, _search_phrase, _make_plural_singular
from werkzeug.utils import secure_filename

app2 = Flask(__name__)
app2.config['UPLOAD_PATH'] = 'uploads'
app2.config['SECRET_KEY'] = 'SillyGoose123!'
app2.config.from_object(__name__)
app2.config['SESSION_TYPE'] = 'filesystem'
Session(app2)

class DataInput(FlaskForm):
    file = FileField('Filename', validators=[FileAllowed(['xlsx']), FileRequired(), InputRequired(message='csv files only!')])


class RemoveButton(FlaskForm):
    Remove = SubmitField('Remove', id="rembtn")

class SubmitTable(FlaskForm):
    submit = SubmitField('Continue', id="cont")

@app2.route('/', methods = ['GET', 'POST'])
def index():
    form = DataInput()

    if form.validate_on_submit():
        #Getting the uploaded file
        file_data = form.file.data
        #file_data2 = form.file_2.data
        #Specifying directory for it to be uploaded
        asset_dir = os.path.join(os.path.dirname(app2.instance_path), 'uploads')
        #Getting filename from data and converting it to a secure filename.
        filename = secure_filename(file_data.filename)
        #Save to uploads folder
        file_data.save(os.path.join(asset_dir, filename))
        #form.file.data.save('uploads/' + filename)

        current_directory = os.getcwd()
        filepath = os.path.join(current_directory, 'uploads', filename)
        data2 = _import_excel(filepath)
        
        #The original terms from ebay that make up remaining keywords.
        session['Original_Sentences'] = data2[0]
        
        session['filename'] = filename
        session['filepath'] = filepath
        session['original_data'] = data2
        session['search_terms'] = []
        session['irrelevant_words'] = []
        result = _remove_words(data2[0], data2[1])
        # Original keywords from CSV plus all negatives.
        original_data = pd.Series(name="Keywords", data=result)
        allnegatives = pd.Series(name="All Negatives", data=data2[1])
        # Store them in session so they can be retrieved
        session['remaining_data'] = original_data
        session['allnegatives_data'] = allnegatives


        return redirect(url_for('keywords'))
            #render_template('index.html', form=form), filename

    else:
        return render_template('index.html', form=form)



@app2.route('/keywords', methods=['POST', 'GET'])
def keywords():

    form = RemoveButton()
    headings = "Remaining Keywords"
    headings2 = "All Negatives"
    headings3 = "Irrelevant"
    data = session.get('remaining_data')
    data2 = session.get('allnegatives_data')
    irrelevant_column = session.get('irrelevant_words')
    print(f'This is your form: {request.form}')

    if request.form.get("search"):
        #WHEN SEARCH BUTTON IS PRESSED

        search_word = request.form.get("SearchWord")
        session['search_term'] = search_word
        #Function which performs the search.
        new_lists = _search_phrase(data, search_word)

        # This block adds the search term plus its pluralised friend to an array and ads it to the session variable search_terms.
        searched_terms = session.get('search_terms')
        # Append a singularised or pluralised version of the searched term and update session.
        searched_terms = _make_plural_singular(search_word, searched_terms)
        print(searched_terms)
        session['search_terms'] = searched_terms

        output = pd.Series(new_lists[0], dtype=object, name="Deconstructed Words")
        headings = "Deconstructed words"
        output = output.drop_duplicates().dropna()
        session['decon_words'] = output

        foundwords = pd.Series(new_lists[1], dtype=object, name="Found Words")
        headings2 = foundwords.name
        data_found = foundwords.iteritems()
        session['found_words'] = foundwords

        return redirect(url_for('irrelevant', form=form, headings=headings, data=output, headings2=headings2, data2=data_found,headings3='All Negatives', data3=irrelevant_column))

    elif request.form.get('field'):
        #WHEN ANY CELL IS EDITED
        field = request.form.get('field')
        if field == "Irrelevant":
            # IF DATA IN THE IRRELEVANT FIELD IS EDITED
            original_data = request.form.get('id')
            new_data = request.form.get('value')
            # If the pandas series for the irrelevant column has been created
            if isinstance(irrelevant_column, pd.Series):
                new_irrelevant_column = irrelevant_column.replace(original_data, new_data)
                session['irrelevant_words'] = new_irrelevant_column
            else:
                #Create the pandas series and replace data
                irrelevant_series = pd.Series(irrelevant_column, name="Irrelevant")
                new_irrelevant_column = irrelevant_series.replace(original_data, new_data)
                session['irrelevant_words'] = new_irrelevant_column

            data = session.get('remaining_data')
            return render_template('keywords.html', form=form, headings=headings, data=data, headings2=headings2,
                                   data2=data2, headings3=headings3, data3=new_irrelevant_column)
        elif field == 'All Negatives':
            original_data = request.form.get('id')
            new_data = request.form.get('value')

            if isinstance(data2, pd.Series):
                new_allneg_column = data2.replace(original_data, new_data)
                session['allnegatives_data'] = new_allneg_column
            else:
                # Create the pandas series and replace data
                allneg_series = pd.Series(data2, name="Irrelevant")
                new_allneg_column = allneg_series.replace(original_data, new_data)
                session['allnegatives_data'] = new_allneg_column

            return render_template('keywords.html', form=form, headings=headings, data=data, headings2=headings2,
                                   data2=new_allneg_column, headings3=headings3, data3=irrelevant_column)

    elif request.form.get('add'):
        # WHEN THE ADD TO IRRELEVANT TABLE BUTTON IS PRESSED.
        # Get information about the word to be added.
        word_to_add = request.form.get('add')

        if isinstance(irrelevant_column, pd.Series):
            # If irrelevant_column is already a pandas series, add to it and update session.
            new_word_series = pd.Series(word_to_add)
            irrelevant_column = new_word_series.append(irrelevant_column).reset_index(drop=True)
            irrelevant_column.drop_duplicates().reset_index(drop=True)
            session['irrelevant_words'] = irrelevant_column

        else:
            # If irrelevant_column is not a pandas series
            # Create a pandas series and add the word corresponding to the "add" button click and update session.
            irrelevant_column = pd.Series(word_to_add)
            irrelevant_column.drop_duplicates().reset_index(drop=True)
            session['irrelevant_words'] = irrelevant_column

        if len(data.index) > 0:
            remaining_words = data.where(~data.str.fullmatch(word_to_add, na=False)).dropna()
            session['remaining_data'] = remaining_words

        session['remaining_data'] = remaining_words

        return render_template('keywords.html', form=form, headings=headings, data=remaining_words, headings2=headings2, data2=data2, headings3=headings3, data3=irrelevant_column)

    elif request.form.get("remove"):

        word_to_remove = request.form.get("remove")
        remaining_words = data.where(~data.str.fullmatch(word_to_remove, na=False)).dropna()
        session['remaining_data'] = remaining_words

        return render_template('keywords.html', form=form, headings=headings, data=remaining_words, headings2=headings2,
                               data2=data2, headings3=headings3, data3=irrelevant_column)

    elif request.form.get("export"):

        #THIS BLOCK HANDLES THE BROAD TERMS
        #Get all broad terms (ie. the ones that have been searched)
        searched_terms_array = session.get('search_terms')
        searched_terms= []
        #Remove all duplicates from the broad terms array
        for i in searched_terms_array:
            if i not in searched_terms:
                searched_terms.append(i)
        
        
                
        #Get all the all negatives terms.
        allnegatives = data2
        # Remove duplicate entries if there are any
        allnegatives.drop_duplicates()

        p = inflect.engine()

        # Remove the index column by converting irrelevant_column to an array
        if isinstance(irrelevant_column, pd.Series):
            irr_column = []
            for index, value in irrelevant_column.iteritems():

                if p.singular_noun(value) != False:
                    #if word is plural make a singular copy and append to array.
                    singular_value = p.singular_noun(value)
                    if singular_value not in irr_column:
                        irr_column.append(singular_value)
                        irr_column.append(f'"{singular_value}"')
                else:
                    #if word is singular, make it plural and append
                    plural_value = p.plural(value)
                    if plural_value not in irr_column:
                        irr_column.append(plural_value)
                        irr_column.append(f'"{plural_value}"')

                # also append the original word.
                if value not in irr_column:
                    irr_column.append(value)
                    irr_column.append(f'"{value}"')
        else:
            irr_column = irrelevant_column

        #Arrange all data into a dictionary
        dict = {'Irrelevant': irr_column,
                'Broad': searched_terms,
                'Exact': [],
                'All Negatives': allnegatives}


        #Adding all of the data into a dataframe.
        output = pd.DataFrame.from_dict(dict, orient='index')
        output = output.transpose()
        #Create a filename that won't conflict with existing files in the folder.
        new_filename = f'Output{uuid.uuid4()}.xlsx'

        #Get the original data from the session and make sure it is a dataframe.
        in_original_data = session.get('original_data')
        if isinstance(in_original_data, pd.DataFrame):
           original_data = in_original_data
           #print(original_data)
        else:
            original_data = pd.DataFrame(in_original_data)
            original_data = original_data.transpose()

        #Initialise pandas excelwriter
        filepath = os.path.join(os.getcwd(), "uploads", f'{new_filename}')
        writer = pd.ExcelWriter(filepath)

        #Create an excel file with two sheets for the original input and the output.
        output.to_excel(writer, sheet_name='Negative Keywords', index=False)
        original_data.to_excel(writer, sheet_name='Original Data')
        writer.save()

        #Save to uploads folder


        return send_file(os.path.join('uploads', new_filename), as_attachment=True,  cache_timeout=0)

    elif request.form.get("home"):

        return render_template('index.html', form=DataInput())

    else:
        return render_template('keywords.html', form=form, headings=headings, data=data, headings2=headings2, data2=data2, headings3=headings3, data3=irrelevant_column)




@app2.route('/irrelevant', methods=['POST', 'GET'])
def irrelevant():
    #This is the page which shows you deconstructed terms after you have searched a term or word.

    #Getting session values
    allnegative = session.get('allnegatives_data')
    remaining_data = session.get('remaining_data')
    decon_words = session.get('decon_words')
    found_words = session.get('found_words')
    headings = 'Deconstructed Words'
    headings2 = 'Found Words'
    headings3 = 'All Negatives'
    print(f'This is your form: {request.form}')

    form = RemoveButton()

    if request.form.get("search"):

        form = RemoveButton()
        #This session search_term is so that the code still runs when nothing is pressed and rerenders.
        search_word = request.form.get("SearchWord")
        print(f'This is your search term: {search_word}')
        session['search_term'] = search_word
        new_lists = _search_phrase(remaining_data, search_word)


        searched_terms = session.get('search_terms')
        #Append a singularised or pluralised version of the searched term and update session.
        searched_terms = _make_plural_singular(search_word, searched_terms)
        print(searched_terms)
        session['search_terms'] = searched_terms

        output = pd.Series(new_lists[0], dtype=object, name="Deconstructed Words")
        output = output.drop_duplicates().dropna()

        headings = "Deconstructed words"
        session['decon_words'] = output

        foundwords = pd.Series(new_lists[1], dtype=object, name="Found Words")
        headings2 = foundwords.name
        session['Found_words'] = foundwords

        return render_template('irrelevant.html', form=form, headings=headings, data=output,
                           headings2=headings2, data2=foundwords, headings3=headings3, data3=allnegative)

    elif request.form.get("move_to_negative"):
        # If button is pressed to move an item in "deconstructed words" to all negatives
        to_negatives = request.form.get('delete')
        series = pd.Series(to_negatives)

        if isinstance(allnegative, pd.Series):
            allnegative2 = series.append(allnegative, ignore_index=True)
            #Update the all negatives list for the session.
            session['allnegatives_data'] = allnegative2
        else:
            all_negative_series = pd.Series(allnegative)
            allnegative2 = series.append(all_negative_series, ignore_index=True)
            session['allnegatives_data'] = allnegative2

        if isinstance(decon_words, pd.Series):
            print("decon_words is a series")
            #Remove the word from the deconstructed list
            decon_words = decon_words.where(~decon_words.str.fullmatch(to_negatives)).dropna()
            session['decon_words'] = decon_words

        else:
            print("decon_words is not a series")
            decon_series = pd.Series(decon_words)
            decon_series = decon_series.where(~decon_series.str.fullmatch(to_negatives)).dropna()
            session['decon_words'] = decon_series

        found = session.get('Found_words')
        return render_template('irrelevant.html', form=form, headings=headings, data=decon_words,
                           headings2=headings2, data2=found_words ,headings3=headings3, data3=allnegative2)

    elif request.form.get("continue"):
        #WHEN CONTINUE IS PRESSED THE NEGATIVE KEYWORDS FROM THE ALL NEGATIVE LIST ARE USED TO REMOVE
        #WORDS FROM THE REMAINING KEYWORDS.


        #Making sure the remaining keyword variable is a pandas Series, if it is
        #Then run the function to remove the keywords matching the negatives
        #If it is not a pandas Series, make it a series first.
        remaining_data = session.get('remaining_data')
        if isinstance(remaining_data, pd.Series):
            new_data = _remove_words(remaining_data, allnegative)
        else:
            remaining_data_ = pd.Series(remaining_data)
            new_data = _remove_words(remaining_data_, allnegative)

        #Update the session variable containing the remaining keywords.
        session['remaining_data'] = new_data
        #Getting session variables to display the correct values on screen.
        irrelevant_column = session.get('irrelevant_words')
        allnegative = session.get('allnegatives_data')
        
        return render_template('keywords.html', form=form, headings="Remaining Keywords", data=new_data, headings2="All Negatives", data2=allnegative, headings3 ='Irrelevant', data3=irrelevant_column)

    elif request.form.get('field'):
        #IF THE CLICKABLE FIELD ON THE ALL NEGATIVE KEYWORD LIST IS ALTERED.

        # Editing a word in the allnegatives column
        irrelevant_column = session.get('irrelevant_words')
        allnegative = session.get('allnegatives_data')
        allnegative_series = pd.Series(allnegative, name='All Negatives')
        # field refers to the original value inside the editable fields
        original_data = request.form.get('field')
        print(f'Original value of cell is: {original_data}')
        # value is the value in the editable field after user clicks outside the cell.
        new_data = request.form.get('value')
        print(f'Changed input is : {new_data}')
        new_all_negatives = allnegative_series.replace(original_data, new_data)
        new_all_negatives.dropna().reset_index(drop=True)
        session['allnegatives_data'] = new_all_negatives

        return render_template('irrelevant.html', form=form, headings="Remaining Keywords", data=new_data,
                               headings2="All Negatives", data2=new_all_negatives, headings3='Irrelevant',
                               data3=irrelevant_column)


    else:
        print("Rendering template")
        return render_template('irrelevant.html', form=form, headings=headings, data=decon_words, headings2=headings2, data2=found_words,headings3=headings3, data3=allnegative)


if __name__ == "__main__":
    app2.run(debug=True)