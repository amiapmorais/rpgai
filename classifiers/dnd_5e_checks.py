# for basic operations
import pandas as pd
import numpy as np
import os
import pickle

# Model Train and Selection
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.svm import SVC
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn import metrics
from sklearn.metrics import confusion_matrix

# For graphics - Confusion Matrix
import seaborn as sns

# for wordcloud analysis
from wordcloud import WordCloud
import matplotlib.pyplot as plt

#for model serialize
from joblib import dump
from sklearn.pipeline import Pipeline

# To get processing time
import time

from NLP_Classifier import NLP_Classifier

class Model_Trainer:
   
    # Class Initialization
    def __init__(self):
        
        # Skills to be identified
        self.lst_skills = [
                            'Acrobatics',
                            'Animal Handling',
                            'Arcana',
                            'Athletics',
                            'Deception',
                            'History',
                            'Insight',
                            'Intimidation',
                            'Investigation',
                            'Medicine',
                            'Nature',
                            'Perception',
                            'Performance',
                            'Persuasion',
                            'Religion',
                            'Sleight of Hand',
                            'Stealth',
                            'Survival'
                            ]
        
        # data sources
        self.CR_url = 'https://raw.githubusercontent.com/amiapmorais/datasets/master/critical_role/skills_dataset.csv'
        self.TK_url = 'https://raw.githubusercontent.com/amiapmorais/datasets/master/tavern_keeper/skills_dataset.csv'
        self.SS_url = 'https://raw.githubusercontent.com/amiapmorais/datasets/master/skill_db.csv'
        self.GP_url = 'https://raw.githubusercontent.com/amiapmorais/datasets/master/podcasts/general_podcasts.csv'
        
        # data to be used
        self.fields_to_use = {'skill', 'backward_text'}
        
        # Modeling parameters
        self.min_obs = 400          # minimun number of observations to sample a skill, otherwise oversample to min_obs
        
        self.nlp = NLP_Classifier()
        
        pass

    # Plot a confusion matrix
    def plot_confusion_matrix(self, title, reals, predictions):
        ax = plt.axes()
        sns.heatmap(confusion_matrix(reals, predictions), xticklabels=self.lst_skills, yticklabels=self.lst_skills, ax=ax)
        ax.set_title(title)
        ax.set_ylabel('Real')
        ax.set_xlabel('Predicted')


    # Load data for modeling
    def data_load(self):
        df_critical_role = pd.read_csv(self.CR_url, usecols=self.fields_to_use)
        # df_tavern_keeper_5e = pd.read_csv(self.TK_url, usecols=self.fields_to_use)
        df_skill_sheet = pd.read_csv(self.SS_url, usecols=self.fields_to_use)
        df_general_podcast = pd.read_csv(self.GP_url, usecols=self.fields_to_use)

        # Flag data source
        df_critical_role['origin'] = 'CR'
        #df_tavern_keeper_5e['origin'] = 'TK'
        df_skill_sheet['origin'] = 'SS'
        df_general_podcast['origin'] = 'GP'

        # Append all dataframes
        list_df = [df_critical_role, df_skill_sheet, df_general_podcast]
        df = df_skill_sheet.append(list_df, ignore_index=True)
        
        return df
    
    
    # Try to make the the training data more homogeneous
    def data_leveler(self, df):
        
        df_sample = pd.DataFrame()
        
        for skill in self.lst_skills:
            # Get number of observations for skill
            num_obs = sum(df['skill'].values == skill)
        
            # Make a more homogeneous dataset for training
            if num_obs > self.min_obs:
                # If skill has more than min_obs, get a sample
                df_skill = df[df['skill'].values == skill].sample(n = self.min_obs).reset_index(drop=True)
            else:
                # If skill has less than min_obs, do an oversample
                df_skill = df[df['skill'].values == skill].sample(n = self.min_obs, replace=True).reset_index(drop=True)
            
            df_sample = df_sample.append(df_skill).reset_index(drop=True)
                
        return df_sample

    
    # Method to create a classification model
    def train_skill_classification(self, path_models):

        # Data Loading
        time_ini = time.time()
        df = self.data_load()
        time_end = time.time()
        print(f"Time for Data Load: {time_end - time_ini} seconds")
        
        # Data Prep
        time_ini = time.time()
        # Drop non mapped skills
        df = df[df.skill.isin(self.lst_skills)].copy().reset_index(drop=True)

        # Check data distribution per skill
        #print(df.skill.value_counts())
                
        # Used for debug of NLP pre processing
        #df_DEBUG = df.groupby('skill').apply(pd.DataFrame.sample, n=5, replace=True).reset_index(drop=True)

        # Drop empty texts before NLP processing
        df_train = df[['skill', 'backward_text']].copy().reset_index(drop = True)
        df_train['backward_text'].replace('', np.nan, inplace=True)
        df_train.dropna(subset=['backward_text'], inplace=True)
        time_end = time.time()
        print(f"Time for Data Prep: {time_end - time_ini} seconds")

        # Data leveler to make training data more homogeneous
        time_ini = time.time()
        # Do an oversampling to get better samples for prediction
        df_estrat = self.data_leveler(df_train)
        time_end = time.time()
        print(f"Time for Data Leveler: {time_end - time_ini} seconds")
        
        # NLP processing
        time_ini = time.time()
        # Bag of words + tf-idf
        bow_tfidf = self.nlp.create_TFIDF_Vec_model(df_estrat['backward_text'].tolist(), path_models)
        time_end = time.time()
        print(f"Time for BOW & TFIDF (include NLP Pre Process): {time_end - time_ini} seconds")
                
        # split data for train and test
        time_ini = time.time()
        X_train, X_test, y_train, y_test = train_test_split(bow_tfidf, df_estrat['skill'], test_size=0.05, random_state = 42)
        time_end = time.time()
        print(f"Time for Train and Test Split: {time_end - time_ini} seconds")

        # Train model        
        time_ini = time.time()
        #clf = LinearSVC()
        #clf = XGBClassifier(objective = 'binary:logistic')
        #clf = SVC() 
        #clf.probability=True
        clf = RandomForestClassifier(n_estimators=200)
        clf = clf.fit(X_train, y_train)
        
         # Save model to disk
        filename = os.path.join(path_models, 'model.sav')
        pickle.dump(clf, open(filename, 'wb'))
        
        time_end = time.time()
        print(f"Time for Model Training: {time_end - time_ini} seconds")
        
        # Score train and test data
        time_ini = time.time()
        y_pred = clf.predict(X_test)
        time_end = time.time()
        print(f"Time for Predict: {time_end - time_ini} seconds")
        
        # Get Train / Test Metrics
        print("")
        print("Train / Test:")
        print(f"Accuracy: {metrics.accuracy_score(y_test, y_pred):.2%}")
        print(f"Precision: {metrics.precision_score(y_test, y_pred, average='macro'):.2%}")
        print(confusion_matrix(y_test, y_pred))
        #plot_confusion_matrix('Train / Test', y_test, y_pred)

        # Get validation metrics
        print("")
        print("Validation:")

        y_val = clf.predict(self.nlp.use_TFIDF_Vec_model(df_train['backward_text'].tolist(), path_models))
        df_train['pred_skill'] = y_val

        print(confusion_matrix(df['skill'], y_val))
        print(f"Validation Accuracy: {metrics.accuracy_score(df['skill'], y_val):.2%}")
        print(f"Validation Precision: {metrics.precision_score(df['skill'], y_val, average='macro'):.2%}")
        self.plot_confusion_matrix('Validation', df['skill'], y_val)
        
        path_data = 'C:\\app\\rpgai\\data\\Dados_Teste.parquet'
        df_train.to_parquet(path_data, index=False)
        

"""
import os
import sys

# Create platform independent import path
# Need to point to the folder that contains the /classifier files
path_pipe = os.path.join(os.path.abspath(os.sep), 'app', 'rpgai', 'classifier')

# Append path to sys path
sys.path.append(path_pipe)

def root_path():
    return os.path.abspath(os.sep)

def folder(*args):
    return os.path.join(root_path(), *args)

# Caminho do parquet com as guias
path_models = folder('app', 'rpgai', 'classifiers', 'models')

mt = Model_Trainer()
mt.train_skill_classification(path_models)

"""


"""
Check some cases to analyze the model
"""
"""
skill_dict = {
            "acrobatics" : "you tumble the strike"
            ,"animal" : "No it is just a regular sized dog that has three heads and is like all blue and ethereal. And they get right up in each others faces, and then just growls at each other, [growling] and both of them are in a dead stop. They are locked eyes at each other."
            ,"athletics" : "So, I'm going to reach up and use the Long Arm of the Law to kind of grapple the edge of the doorway, and then kind of like ferry people up and climb up my body and my arm to the doorway."
            ,"arcana" : "Hey, am I passively sensing any kind of magic?"
            ,"deception" : "We want to look like nondescript peasants. So if somebody saw us there, they would assume we were there to clean, to deliver food, to do whatever needs doing in the house."
            ,"history" : "I guess I haven't seen it in a really long time I don’t know where it is. I am looking for this uh mouthpiece, I don’t know what it’s attached to now. But it looks like a very large open mouth and it’s laughing, and it has really bright red lips and I don’t know if you’ve seen it before, but if you see it I would love to get my hand on it cause I think it’s tied to all these things happening right now."
            ,"insight" : "Like a suggestive wink or like we're on the same team wink? Can I investigate the wink?"
            ,"intimidation" : "I am going to push my cloak aside to have one hand and my dagger and hold my hand up knowing that I cannot stop him with the body force but I can stop him with intimidation and say"
            ,"investigation" : "I’d love to search the ceiling to see if there are any hatches."
            ,"medicine" : "Johnny, do you know anything about this frozen poison type thing? Can you help him right now?"
            ,"nature" : "I think back on my adventures in nature to perhaps recognize what they are."
            ,"perception" : "Do I notice anything dangerous?"
            ,"performance" : "And pulls out his help horn, runs across the room while blowing it and then pulls his maroon cape in front of him as if he's egging Nessie on."
            ,"persuasion" : "But when this is all over and we trap the Council, and everything goes back to normal, I don’t want anyone to know who I am. I want a fresh start. Except for the friends and the family I made. Inara should know, and everyone else, Evan. But the world at large, I don’t want any fame, fortune, I just want to go. I don’t want anyone to know I’m the reason this started, this whole thing started. I just want to go sell tea."
            ,"religion" : "I would like my religious senses to let me know any kind of divine interference that might be going on."
            ,"sleight" : "Before Bridge walks away, Inara’s going to pickpocket him for gold."
            ,"stealth" : "Come out that side and then get up into the ring, behind the barrel as cover, and then attack the guy that way."
            ,"survival" : "The atmosphere is breaking his concentration on his main task of checking around the party for travelling advantages...!"
            }
"""
"""
REMEMBER TO USE THE SAME TEXT THAT WAS USED TO TRAIN THE MODEL!!!
"""
"""
def check_for_skill(skill_name, skill, n):
    tokens, stemms, lemmas = nlp_preprocess(skill)
    y_valid = clf.predict(vectorizer.transform([lemmas]))
    y_valid_prob = clf.predict_proba(vectorizer.transform([lemmas]))
    
    # Print best n matches
    best_n = np.argsort(y_valid_prob, axis=1)[:,-n:]
    classes = clf.classes_
    print('')
    print(f'Expected: {skill_name}')
    print(f'Predicted: {y_valid[0]}')
    
    # TO DO >>> Loop the n options >> need to do !!!
    print(f'First predicted class = {classes[best_n[0, 2]]} and confidence = {y_valid_prob[0, best_n[0, 2]]:.2%}')
    print(f'Second predicted class = {classes[best_n[0, 1]]} and confidence = {y_valid_prob[0, best_n[0, 1]]:.2%}')
    print(f'Third predicted class = {classes[best_n[0, 0]]} and confidence = {y_valid_prob[0, best_n[0, 0]]:.2%}')
    return y_valid

# Skill Check to validate
for skill in skill_dict:
    skill_to_check = check_for_skill(skill, skill_dict[skill], 3)

"""
"""
To check a single text
"""
"""
skill_real = 'Acrobatics'
text = 'I do a back somersault to avoid being hit'
skill_dict = {skill_real : text}
check_for_skill(skill_real, skill_dict[skill_real], 3)

"""
"""
Wordcloud using tfidf features
"""
"""
### Melhorar isso aqui
# The data frame needs the skill and train_text columns
df1 = pd.DataFrame(vectorizer.get_feature_names(), columns=['text'])

def wordcloud(text):
  wordcloud = WordCloud(background_color="white").generate(text)
  plt.figure(figsize=(10,10))
  plt.imshow(wordcloud, interpolation='bilinear')
  plt.axis("off")

wordcloud(' '.join(df1['text']))

"""

def run_pipeline():
    pipeline = Pipeline(steps= [('tfidf', TfidfVectorizer(analyzer = 'word', max_df = 0.90, min_df = 3,
    ngram_range=(1, 2), stop_words=new_stopwords)),
    ('model', RandomForestClassifier(n_estimators = 200))])
    # fit the pipeline model with the training data 
    pipeline.fit(df_estrat['train_text'], df_estrat['skill'])

    # dump the pipeline model
    dump(pipeline, filename='text_classification.joblib')

