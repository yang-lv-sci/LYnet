# -*- coding: utf-8 -*-
"""
Created on Sun Jul 17 07:42:37 2022

@author: lvyang
"""

import pandas as pd
import numpy as np
from tensorflow.keras import models,layers,optimizers,regularizers
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import roc_curve,auc
import matplotlib.pyplot as plt
import tensorflow as tf

earlystop_callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss', min_delta=0.0001,patience=80,mode="min")

aaindex=pd.read_table('aaindex31',sep='\s+',header=None)
aaindex=aaindex.subtract(aaindex.min(axis=1),axis=0).divide((aaindex.max(axis=1)-aaindex.min(axis=1)),axis=0)
aa=[x for x in 'ARNDCQEGHILKMFPSTWYV']
aaindex=aaindex.to_numpy().T
index={x:y for x,y in zip(aa,aaindex.tolist())}
index['-']=np.zeros(31).tolist()

def cnn(max_len,depth,l1=32,l2=256,gamma=1e-4,lr=1e-4,w1=3,w2=2):
    model=models.Sequential()
    model.add(layers.Conv1D(l1,w1,activation='relu',kernel_regularizer=regularizers.l1(gamma),input_shape=(max_len,depth),padding='same'))
    model.add(layers.MaxPooling1D(w2))
    model.add(layers.Flatten())
    model.add(layers.Dropout(0.5))
    
    model.add(layers.Dense(l2,activation='relu',kernel_regularizer=regularizers.l2(gamma)))
    model.add(layers.Dense(l2,activation='relu',kernel_regularizer=regularizers.l2(gamma)))
    
    model.add(layers.Dense(1,activation='sigmoid',kernel_regularizer=regularizers.l2(gamma)))
    
    """model.compile(loss='binary_crossentropy',
                  optimizer=optimizers.RMSprop(lr=lr),
                  metrics=['acc'])"""
    
    adam = Adam(learning_rate=lr, beta_1=0.9, beta_2=0.999, epsilon=1e-08)
    model.compile(optimizer=adam, loss="binary_crossentropy", metrics=['acc'])
    
    return model

def read_data(lines):
    label=[]
    seq=[]
    for i  in range(len(lines)):
        if i%2==0:
            temp=[]
            temp.extend(lines[i])
            if "n" in temp:
                label.append(0)
            else:
                label.append(1)
        else:
            seq.append(lines[i][:-1])
    return seq,np.array(label)

def aminoacids_encode(seq,max_len):
    encoding=[]
    for i in seq:
        s=[]
        for x in i:
            s.extend(x)
        s=s+(max_len-len(i))*["-"]
        encoding.append([index[x] for x in s])
    return encoding

f=open("seqset/Train.FASTA",'r')
train_lines=f.readlines()
train_seq,train_label=read_data(train_lines)
f.close()

f=open("seqset/Test.FASTA",'r')
test_lines=f.readlines()
test_seq,test_label=read_data(test_lines)
f.close()

padding_lens= len(max(max(train_seq, key=len, default=''),max(test_seq, key=len, default='')))

train_encoding=np.array(aminoacids_encode(train_seq, padding_lens))
row=train_encoding.shape[1]
column=train_encoding.shape[2]
train_encoding=np.reshape(train_encoding,(len(train_encoding),row*column))

# 使用imlbearn库中上采样方法中的SMOTE接口
from imblearn.over_sampling import SMOTE
# 定义SMOTE模型，random_state相当于随机数种子的作用
oversample = SMOTE()
train_encoding,train_label=oversample.fit_resample(train_encoding,train_label)

train_encoding=np.reshape(train_encoding,(len(train_encoding),row,column))

test_encoding=np.array(aminoacids_encode(test_seq, padding_lens))

"""随机化处理"""

np.random.seed(0)
shuffle_list=[]
while True:
    i=np.random.randint(0,train_encoding.shape[0])
    if i not in shuffle_list:
        shuffle_list.append(i)
    if len(shuffle_list)==train_encoding.shape[0]:
        break

train_encoding_shuffle=train_encoding[shuffle_list]
train_label_shuffle=train_label[shuffle_list]

train_encoding=train_encoding_shuffle
train_label=train_label_shuffle

"""k=10
np.random.seed(1234)

num=len(train_label)
mode1=np.arange(num/2)%k
mode2=np.arange(num/2)%k
np.random.shuffle(mode1)
np.random.shuffle(mode2)
mode=np.concatenate((mode1,mode2))
score_aaindex_cnn=np.zeros(num)

for fold in range(k):
    
    trainLabel=train_label[mode!=fold]
    testLabel=train_label[mode==fold]
    
    trainFeature1=train_encoding[mode!=fold]
    testFeature1=train_encoding[mode==fold]
    
    m1=cnn(padding_lens,31)
    m1.fit(trainFeature1,trainLabel,batch_size=trainLabel.shape[0],epochs=10000,verbose=1,validation_data=(testFeature1,testLabel),
           shuffle=True,callbacks=[earlystop_callback])
    score_aaindex_cnn[mode==fold]=m1.predict(testFeature1).reshape(len(testFeature1))
    
np.savez('cnntrain.npz',cnn=score_aaindex_cnn,label=train_label)"""

model=cnn(padding_lens,31)
model.fit(train_encoding,train_label,batch_size=256,epochs=10000,verbose=1,validation_data=(test_encoding,test_label),
          shuffle=True,callbacks=[earlystop_callback])
test_preidct=model.predict(test_encoding).reshape(len(test_encoding))


np.savez('cnntest.npz',cnn=test_preidct,label=test_label)

#train=np.load("cnntrain.npz")
test=np.load("cnntest.npz")

#fpr,tpr,_=roc_curve(train['label'],train['cnn'])
fpr1,tpr1,_=roc_curve(test['label'],test['cnn'])
lw = 1
plt.subplot(121)
plt.plot(fpr1, tpr1, color='green',lw=lw, label='CNN-aaindex-test     AUC = {:.3f}'.format(auc(fpr1,tpr1)))
#plt.plot(fpr, tpr, color='red',lw=lw, label='CNN-aaindex-train-ten-cross-validation     AUC = {:.3f}'.format(auc(fpr,tpr)))
plt.plot([0, 1], [0, 1], color='grey', lw=lw, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.legend(loc="lower right")
plt.show()
