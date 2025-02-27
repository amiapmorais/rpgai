# for NLP preprocessing
import pandas as pd
import re
import spacy
from nltk.stem.snowball import SnowballStemmer
from unidecode import unidecode
import numpy as np

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

# Cleans text from processing and tokenizing
def clean_text(text):
    text = text.lower()
    t = unidecode(text)
    t.encode("ascii")  
    t = re.sub(r'[^a-z]', ' ', t)           #Remove nonalpha
    t = re.sub(r'\s[^a-z]\s', ' ', t)       #Remove nonalpha >> check if is really necessary!?!?
    t = re.sub(r"\b[a-z]{1,2}\b", ' ', t)   #Remove words with 1 or 2 letters
    t = re.sub(' +', ' ', t)                #Remove extra spaces
    t = t.strip()                           #Remove leading and trailing spaces
    return t

# NLP Pre process
def nlp_preprocess(text):
    
    tokens = []
    lemmas = []
    stemms = []

    doc = nlp(text)
    
    for token in doc:
        if not token.is_stop: 
            if (token.pos_ == 'VERB' or token.pos_ == 'NOUN' or token.pos_ == 'ADJ'):
                tokens.append(token.text)
                lemmas.append(token.lemma_)
                stemms.append(stemmer.stem(token.text))
    
    return clean_text(' '.join(tokens)), clean_text(' '.join(stemms)), clean_text(' '.join(lemmas))

def plot_confusion_matrix(title, reals, predictions):
    ax = plt.axes()
    sns.heatmap(confusion_matrix(reals, predictions), xticklabels=skills, yticklabels=skills, ax=ax)
    ax.set_title(title)
    ax.set_ylabel('Real')
    ax.set_xlabel('Predicted')


# Skills to be identified
skills = [
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

#data sources
CR_url = 'https://raw.githubusercontent.com/amiapmorais/datasets/master/critical_role/skills_dataset.csv'
TK_url = 'https://raw.githubusercontent.com/amiapmorais/datasets/master/tavern_keeper/skills_dataset.csv'
SS_url = 'https://raw.githubusercontent.com/amiapmorais/datasets/master/skill_db.csv'
GP_url = 'https://raw.githubusercontent.com/amiapmorais/datasets/master/podcasts/general_podcasts.csv'

#data to be used
fields = {'skill', 'backward_text'}

df_critical_role = pd.read_csv(CR_url, usecols=fields)
df_tavern_keeper_5e = pd.read_csv(TK_url, usecols=fields)
df_skill_sheet = pd.read_csv(SS_url, usecols=fields)
df_general_podcast = pd.read_csv(GP_url, usecols=fields)

# Flag data source
df_critical_role['origin'] = 'CR'
df_tavern_keeper_5e['origin'] = 'TK'
df_skill_sheet['origin'] = 'SS'
df_general_podcast['origin'] = 'GP'

"""
DEBUG - Alguma fonte de dados está zoada!!!
df_tavern_keeper_5e >> Está com dados zoados >> prejudica o modelo
df_DEBUG = df.groupby('skill').apply(pd.DataFrame.sample, n=5, replace=True).reset_index(drop=True)
"""
# Append all dataframes
list_df = [df_critical_role, df_skill_sheet, df_general_podcast]
df = df_skill_sheet.append(list_df, ignore_index=True)

# Drop non mapped skills
df = df[df.skill.isin(skills)]

# Check data distribution per skill
df.skill.value_counts()

"""
Start NLP Pre Process
"""
nlp = spacy.load("en_core_web_sm")
stemmer = SnowballStemmer(language='english')

# Do NLP pre process in a single step
df['token_text'], df['stemm_text'], df['lemma_text'] = zip(*df['backward_text'].map(nlp_preprocess))

# Used for debug of NLP pre processing
#df_DEBUG = df.groupby('skill').apply(pd.DataFrame.sample, n=5, replace=True).reset_index(drop=True)

"""
SET HERE THE TEXT TO BE USED IN MODEL TRAINING
"""
df['train_text'] = df['stemm_text']

# Drop empty texts after NLP pre processing
df_train = df[['skill', 'train_text']].copy()
df_train['train_text'].replace('', np.nan, inplace=True)
df_train.dropna(subset=['train_text'], inplace=True)

# Do an oversampling to get better samples for prediction
df_estrat = df_train.groupby('skill').apply(pd.DataFrame.sample, n=400, replace=True).reset_index(drop=True)

### Usar dicionário de termos sinônimos?!?!

### Stopwords
new_stopwords = [
                #Common words
                "going", "right", "okay", "yeah", "want", "try", "gonna", "good", "yes", "look", "know", "way", "guy",
                "little", "check", "thin", "thing", "guys", "come", "roll", "let", "time", "got", "maybe", "think", 
                "fuck", "lot", "shit", "bit", "point",
                #PCs and NPCs Names
                "jester", "caleb", "nott", "fjord", "yasha", "beau", "matt", "sam", "travis", "marisha", "ashley", "laura", 
                "liam", "professor", "thaddeus", "taliesin", "mollymauk", "grog", "pike"
                ]


# Bag of words + tf-idf
vectorizer = TfidfVectorizer(analyzer = 'word', max_df = 0.90, min_df = 3, ngram_range=(1, 2), stop_words=new_stopwords)
bow_tfidf = vectorizer.fit_transform(df_estrat['train_text'])

# split data for train and test
### Montar dataset de validação
X_train, X_test, y_train, y_test = train_test_split(bow_tfidf, df_estrat['skill'], test_size=0.05, random_state = 42)

# Train Model
#clf = LinearSVC()
#clf = XGBClassifier(objective = 'binary:logistic')
#clf = SVC() 
#clf.probability=True
clf = RandomForestClassifier(n_estimators=200)
clf = clf.fit(X_train, y_train)
y_pred = clf.predict(X_test)

"""
Neural Network Test
"""

### FAZER ENCODING DO LABEL
from keras.models import Sequential
from keras import layers

skill_encode = {
            "Acrobatics" : 0
            ,"Animal Handling" : 1
            ,"Athletics" : 2
            ,"Arcana" : 3
            ,"Deception" : 4
            ,"History" : 5
            ,"Insight" : 6
            ,"Intimidation" : 7
            ,"Investigation" : 8
            ,"Medicine" : 9
            ,"Nature" : 10
            ,"Perception" : 11
            ,"Performance" : 12
            ,"Persuasion" : 13
            ,"Religion" : 14
            ,"Sleight of Hand" : 15
            ,"Stealth" : 16
            ,"Survival" : 17
            }

df_estrat['skill_encoded'] = df_estrat['skill'].replace(skill_encode)
X_train, X_test, y_train, y_test = train_test_split(bow_tfidf, df_estrat['skill_encoded'], test_size=0.2, random_state = 42)
print(y_train)

input_dim = X_train.shape[1]  # Number of features

model = Sequential()
model.add(layers.Dense(10, input_dim=input_dim, activation='relu'))
model.add(layers.Dense(1, activation='sigmoid'))

model.compile(loss='binary_crossentropy', 
              optimizer='adam', 
              metrics=['accuracy'])
model.summary()

history = model.fit(X_train, y_train,
                    epochs=100,
                    verbose=False,
                    validation_data=(X_test, y_test),
                    batch_size=10)

loss, accuracy = model.evaluate(X_train, y_train, verbose=False)
print("Training Accuracy: {:.4f}".format(accuracy))
loss, accuracy = model.evaluate(X_test, y_test, verbose=False)
print("Testing Accuracy:  {:.4f}".format(accuracy))

# Get Train / Test Metrics
print("")
print("Train / Test:")
print(f"Accuracy: {metrics.accuracy_score(y_test, y_pred):.2%}")
print(f"Precision: {metrics.precision_score(y_test, y_pred, average='macro'):.2%}")
print(confusion_matrix(y_test, y_pred))
plot_confusion_matrix('Train / Test', y_test, y_pred)

# Get validation metrics
print("")
print("Validation:")
y_val = clf.predict(vectorizer.transform(df['train_text']))
print(confusion_matrix(df['skill'], y_val))
print(f"Validation Accuracy: {metrics.accuracy_score(df['skill'], y_val):.2%}")
print(f"Validation Precision: {metrics.precision_score(df['skill'], y_val, average='macro'):.2%}")
plot_confusion_matrix('Validation', df['skill'], y_val)


"""
Check some cases to analyze the model
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
REMEMBER TO USE THE SAME TEXT THAT WAS USED TO TRAIN THE MODEL!!!
"""
def check_for_skill(skill_name, skill, n):
    tokens, stemms, lemmas = nlp_preprocess(skill)
    y_valid = clf.predict(vectorizer.transform([stemms]))
    y_valid_prob = clf.predict_proba(vectorizer.transform([stemms]))
    
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
Wordcloud using tfidf features
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