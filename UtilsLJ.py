import sugartensor as tf
import numpy as np
from scipy.io import savemat
import sys
from scipy.io import loadmat
import pandas as pd
import numpy as np
import sugartensor as tf
import numpy as np
import pandas as pd
import time
from scipy.io import loadmat
import os
np.random.seed(0)

#########################
def write_to_tfrecords(dataMat,tfFileDirName):
    """
    example:
    write_to_tfrecords(dictionary{'x':np.array,...},'./Data/digits.tfrecords') Needs to remember the dimension and name of the dictionary data.
    return: tfrecords saved in given tfFileDirName
    """
    varNames=[i for i in list(dataMat.keys())]
    
    tmpData={}
    tmpShape={}
    
    for i in varNames:
        tmpData[i]=dataMat[i]
        tmpShape[i]=dataMat[i].shape
  
    ####Check shape and Nan############
    if (len(set([tmpShape[i][0] for i in tmpShape.keys()]))!=1) or \
    (np.sum([np.isnan(tmpData[i]).sum() for i in tmpData.keys()])!=0):
        print("Unbalance Label or NaN in Data")
        return
    ###################################
    writer = tf.python_io.TFRecordWriter(tfFileDirName)
    for i in range(len(tmpData[varNames[0]])):
        tmpFeature={}
        for ii in varNames:
            tmp=np.asarray(tmpData[ii][i], dtype=np.float32).tobytes()
            
            tmpFeature[ii]=tf.train.Feature(bytes_list=tf.train.BytesList(value=[tmp]))
            
        example = tf.train.Example(features=tf.train.Features(feature=tmpFeature))    
        writer.write(example.SerializeToString())
    writer.close()  
    print("writing successfully in your dir:{}".format(tfFileDirName))
    
    
def read_from_tfrecords(tfFileDirName,varNames,sizeBatch,shape,shuffle=True,rs=888):
    """
    example:
    read_from_tfrecords('./Data/digits.tfrecords',['x','y'],32,[[28,28],[1]])
    
    return: list of tensors. (this function should be only used in tensorflow codes)
    """
    varNames=list(varNames)
    tmp=[np.asarray(i,dtype=np.int32) for i in shape]
    shape=[]
    for i in tmp:
        if np.sum(np.shape(i))>1:
            shape.append(list(i))
        else:
            shape.append([int(i)])
    
    # print([tfFileDirName])
    filename_queue = tf.train.string_input_producer(tfFileDirName)
    reader = tf.TFRecordReader()
    _, serialized_example = reader.read(filename_queue)
    tmpFeatures={}
    for ii in varNames:
        tmpFeatures[ii]=tf.FixedLenFeature([], tf.string)
    tmpFeatures = tf.parse_single_example(serialized_example,
                                       features=tmpFeatures)  
    tmpVar=[]
    for i in range(len(varNames)):
        ii=varNames[i]
        tmp=tf.decode_raw(tmpFeatures[ii], tf.float32)
        tmp=tf.reshape(tmp, shape=list(shape[i]))
        tmpVar.append(tmp)
        
    if shuffle:
        tmpBatch=tf.train.shuffle_batch(tmpVar, sizeBatch, capacity=sizeBatch * 128,
                              min_after_dequeue=sizeBatch * 32, name=None, seed=rs)
    else:
        tmpBatch=tf.train.batch(tmpVar, sizeBatch, capacity=sizeBatch * 128, name=None)
        
    return tmpBatch    

########################################################

def shuffle_data(data, labels):
    """ Shuffle data and labels.
        Input:
          data: B,N,... numpy array
          label: B,... numpy array
        Return:
          shuffled data, label and shuffle indices
    """
    idx = np.arange(len(labels))
    np.random.shuffle(idx)
    return data[idx, ...], labels[idx], idx


def rotate_point_cloud(batch_data):
    """ Randomly rotate the point clouds to augument the dataset
        rotation is per shape based along up direction
        Input:
          BxNx3 array, original batch of point clouds
        Return:
          BxNx3 array, rotated batch of point clouds
    """
    rotated_data = np.zeros(batch_data.shape, dtype=np.float32)
    for k in range(batch_data.shape[0]):
        rotation_angle = np.random.uniform() * 2 * np.pi
        cosval = np.cos(rotation_angle)
        sinval = np.sin(rotation_angle)
        rotation_matrix = np.array([[cosval, 0, sinval],
                                    [0, 1, 0],
                                    [-sinval, 0, cosval]])
        shape_pc = batch_data[k, ...]
        rotated_data[k, ...] = np.dot(shape_pc.reshape((-1, 3)), rotation_matrix)
    return rotated_data


def rotate_point_cloud_by_angle(batch_data, rotation_angle):
    """ Rotate the point cloud along up direction with certain angle.
        Input:
          BxNx3 array, original batch of point clouds
        Return:
          BxNx3 array, rotated batch of point clouds
    """
    rotated_data = np.zeros(batch_data.shape, dtype=np.float32)
    for k in range(batch_data.shape[0]):
        #rotation_angle = np.random.uniform() * 2 * np.pi
        cosval = np.cos(rotation_angle)
        sinval = np.sin(rotation_angle)
        rotation_matrix = np.array([[cosval, 0, sinval],
                                    [0, 1, 0],
                                    [-sinval, 0, cosval]])
        shape_pc = batch_data[k, ...]
        rotated_data[k, ...] = np.dot(shape_pc.reshape((-1, 3)), rotation_matrix)
    return rotated_data


def jitter_point_cloud(batch_data, sigma=0.01, clip=0.05):
    """ Randomly jitter points. jittering is per point.
        Input:
          BxNx3 array, original batch of point clouds
        Return:
          BxNx3 array, jittered batch of point clouds
    """
    B, N, C = batch_data.shape
    assert(clip > 0)
    jittered_data = np.clip(sigma * np.random.randn(B, N, C), -1*clip, clip)
    jittered_data += batch_data
    return jittered_data

def getDataFiles(list_filename):
    return [line.rstrip() for line in open(list_filename)]

def load_h5(h5_filename):
    f = h5py.File(h5_filename)
    data = f['data'][:]
    label = f['label'][:]
    return (data, label)

def loadDataFile(filename):
    return load_h5(filename)

def load_h5_data_label_seg(h5_filename):
    f = h5py.File(h5_filename)
    data = f['data'][:]
    label = f['label'][:]
    seg = f['pid'][:]
    return (data, label, seg)


def loadDataFile_with_seg(filename):
    return load_h5_data_label_seg(filename)













####################################################

def Generator11(middle,sizeBch=32):
    reuse = len([t for t in tf.global_variables() if t.name.startswith('generator')]) > 0
    with tf.sg_context(name='generator', stride=2, act='leaky_relu', bn=True, reuse=reuse):
        fc1g = middle.sg_dense(dim=512,name='gen1')
        fc1g = fc1g.sg_dense(dim=512*4*4*4, name='gen2')
        fc1greshape=fc1g.sg_reshape(shape=(-1, 4, 4, 4, 512), name='gen3')
        conv3d1g = fc1greshape.sg_deconv3d(dim=256, stride=2, size=4, name='gen4', sizeBatch=sizeBch)
        conv3d2g = conv3d1g.sg_deconv3d(dim=128, stride=2, size=4, name='gen5', sizeBatch=sizeBch)
        out = conv3d2g.sg_deconv3d(dim=1, stride=2, size=4, act='sigmoid', bn=False, name='gen6', sizeBatch=sizeBch)
        out = out.sg_reshape(shape=(-1, 32*32*32))
    return out
    

def Discriminator11(x, alpha=0.5, sizeBch=32, gg=False, middim=100):
        # reuse flag
    reuse = len([t for t in tf.global_variables() if t.name.startswith('discriminator')]) > 0
    with tf.sg_context(name='discriminator', stride=2, act='leaky_relu', bn=True, reuse=reuse):
        x=x+tf.random_normal(shape=tf.shape(x),mean=0.0,stddev=0.1)
        tensor = (x
                  .sg_reshape(shape=(-1, 32, 32, 32, 1))
                  .sg_conv3d(dim=64, size=4, name='dis1a')
                  .sg_conv3d(dim=128, size=4, name='dis2a')
                  .sg_conv3d(dim=256, size=4, name='dis3a')
                  .sg_flatten())
        
        middle = tensor.sg_dense(dim=middim, name="dis1", act='linear', bn=True)
        fc1g = middle.sg_dense(dim=512,name='dis2')
        fc1g = fc1g.sg_dense(dim=512*4*4*4, name='dis3')
        fc1greshape=fc1g.sg_reshape(shape=(-1, 4, 4, 4, 512), name='dis4')
        conv3d1g = fc1greshape.sg_deconv3d(dim=256, stride=2, size=4, name='dis5', sizeBatch=sizeBch)
        conv3d2g = conv3d1g.sg_deconv3d(dim=128, stride=2, size=4, name='dis6', sizeBatch=sizeBch)
        out = conv3d2g.sg_deconv3d(dim=1, stride=2, size=4, act='linear', bn=True, name='dis7', sizeBatch=sizeBch)
        out = out.sg_reshape(shape=(-1, 32*32*32))
        
        #if gg:
        ##    out1=tf.where(x>0.5,tf.ones_like(out),tf.zeros_like(out))
        #   loss = -tf.reduce_mean(alpha * out1 * tf.log(1e-6 + x) + (1 - alpha)*(1 - out1) * tf.log(1e-6 + 1 - x), 1)
        #   loss = tf.reduce_mean(loss) 
            #loss = tf.reduce_mean()
        #else:
        #    loss = -tf.reduce_mean(alpha * x * tf.log(1e-6 + out) + (1 - alpha)*(1 - x) * tf.log(1e-6 + 1 - out), 1)
        #    loss = tf.reduce_mean(loss)

        resid=tf.abs(x-out)
        loss=tf.reduce_mean(resid)
    return loss, out

def Classifier3D11(x,nClasses,dim):
    reuse = len([t for t in tf.global_variables() if t.name.startswith('classifier')]) > 0
    with tf.sg_context(name='classifier', stride=2, act='relu', bn=True, reuse=reuse):
        tensor = (x
                  .sg_reshape(shape=(-1, dim, dim, dim, 1))
                  .sg_conv3d(dim=64, size=4, name='dis1a')
                  .sg_conv3d(dim=128, size=4, name='dis2a')
                  .sg_conv3d(dim=256, size=4, name='dis3a')
                  .sg_flatten())
        
        fc1 = tensor.sg_dense(dim=100, name="dis1", act='linear', bn=True)
        fc2=fc1.sg_dense(dim=nClasses,name="dis2",act="sigmoid",bn=False)
    return fc2

    
#######################################################################################################
def volume_to_3d(dd):
    temp=np.asarray(np.where(dd!=0)).T
    return temp

def ddd_to_volume(vo,ss):
    [hi,wi,le]=ss
    temp=np.zeros(ss)
    for i in range(len(vo)):
        #a=np.maximum(vo[i][0],31)
        #b=np.maximum(vo[i][1],31)
        #c=np.maximum(vo[i][2],31)
        temp[vo[i][0]][vo[i][1]][vo[i][2]]=1
    return temp

def make_dummy(y_test):
    tt=np.zeros((len(y_test),len(set(y_test))))
    a=list(set(y_test))
    a.sort()
    for i in range(len(y_test)):
        j=a.index(y_test[i])
        tt[i,j]=1
    return tt

def shift_to_middle(d,dim):
    d=d-d.min(axis=0)
    d=d+(dim-1-(d.max(axis=0)-d.min(axis=0)))/2
    return d 

def rotate_90_degree_vol(v):
    v=v.reshape(32,32,32)
    v=volume_to_3d(v)
    vv=np.dot(np.asarray([[0,-1,0],
                         [1,0,0],
                         [0,0,1]]),v.T).T
    return ddd_to_volume(vv,(32,32,32))

def rotate_90_degree(v):
    vv=np.dot(np.asarray([[0,-1,0],
                         [1,0,0],
                         [0,0,1]]),v.T).T
    return vv

###########################################
def TransformToTFRecordsMat(matname,rotate=False):
    import numpy as np 
    import pandas as pd
    import sklearn
    import binvox_rw
    import scipy
    cwd = os.getcwd()
    ddf = loadmat('./Data/'+matname+'.mat')
    ddim=32
    x_train=ddf["x"][:1000]
    x_train_3d=[]
    for i in range(len(x_train)):
        d=volume_to_3d(x_train[i])
        d=shift_to_middle(d,ddim)
        globals()['fk']=d
        d3=ddd_to_volume(d,(ddim,ddim,ddim))
        if rotate:
            d3=rotate_90_degree(d3)
        x_train_3d.append(d3)
    
    x_train_3d=np.asarray(x_train_3d)
    print(x_train_3d.shape)  
    y_train=["cla1"]*len(x_train_3d)
    y_train = make_dummy(y_train)
    print(y_train.shape)
    WriteToTFRecords(matname, x_train_3d, y_train)
    
def WriteToTFRecords(name, data_3d,data_img):
    # accept data, label as list
    writer = tf.python_io.TFRecordWriter(name+".tfrecords")
    index = np.arange(len(data_3d))
    for m in range(len(data_3d)):
        ind=index[m]
        d=np.asarray(data_3d[ind], dtype=np.float32)
        d_p=np.asarray(data_img[ind], dtype=np.float32)

        d_raw = d.tobytes()
        d_p_raw=d_p.tobytes()
        example = tf.train.Example(features=tf.train.Features(feature={
            'd_raw': tf.train.Feature(bytes_list=tf.train.BytesList(value=[d_raw])),
            'd_p_raw': tf.train.Feature(bytes_list=tf.train.BytesList(value=[d_p_raw]))
        }))
        writer.write(example.SerializeToString())
    writer.close()
    
############Inception Score################
def cal_incep_score(preds,splits=10):    
    scores = []
    for i in range(splits):
        part = preds[(i * preds.shape[0] // splits):((i + 1) * preds.shape[0] // splits), :]
        kl = part * (np.log(part) - np.log(np.expand_dims(np.mean(part, 0), 0)))
        kl = np.mean(np.sum(kl, 1))
        scores.append(np.exp(kl))
    return np.mean(scores), np.std(scores)
###########################################

def volumeVis(ddd,th):
    import matplotlib.pylab as plt
    from mpl_toolkits.mplot3d import Axes3D
    ddd=ddd.reshape(32,32,32)
    ddd=ddd>th
    d=volume_to_3d(ddd)
    fig = plt.figure(1, figsize=(2, 2))
    ax = fig.add_subplot(1, 1, 1, projection='3d')
    ax.scatter(d[:, 0],d[:, 1],d[:, 2])
    ax.set_xlim(0,32)
    ax.set_ylim(0,32)
    ax.set_zlim(0,32)
    plt.show()  

def VisBat(aa,bb,cc,th,n):
    import matplotlib.pylab as plt
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure(1, figsize=(5, 30))
    for j in range(len(aa))[:n]:
            dd=np.asarray((aa[j])).reshape(64,64,3)
            fig = plt.figure(1, figsize=(3, 3))
            ax = fig.add_subplot(32, 3, j*3+1)
            ax.imshow(dd)
            ax.axis('off')
            
            dd=np.asarray((bb[j]>th)).reshape(32,32,32)
            d=volume_to_3d(dd)
            fig = plt.figure(1, figsize=(3, 3))
            ax = fig.add_subplot(32, 3, j*3+2, projection='3d')
            ax.scatter(d[:, 0],d[:, 1],d[:, 2],s=1)
            ax.set_xlim(0,32)
            ax.set_ylim(0,32)
            ax.set_zlim(0,32)
            ax.axis('off')
            
                        
            dd=np.asarray((cc[j]>th)).reshape(32,32,32)
            d=volume_to_3d(dd)
            fig = plt.figure(1, figsize=(3, 3))
            ax = fig.add_subplot(32, 3, j*3+3, projection='3d')
            ax.scatter(d[:, 0],d[:, 1],d[:, 2],s=1)
            ax.set_xlim(0,32)
            ax.set_ylim(0,32)
            ax.set_zlim(0,32)
            ax.axis('off')
    plt.show()   
    
def VisBatPic(aa,bb):
    import matplotlib.pylab as plt
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure(1, figsize=(5, 30))
    for j in range(len(aa))[:n]:
            dd=np.asarray((aa[j])).reshape(64,64,3)
            fig = plt.figure(1, figsize=(3, 3))
            ax = fig.add_subplot(32, 3, j*3+1)
            ax.imshow(dd)
            ax.axis('off')
            
            dd=np.asarray((bb[j])).reshape(64,64,3)
            fig = plt.figure(1, figsize=(3, 3))
            ax = fig.add_subplot(32, 3, j*3+1)
            ax.imshow(dd)
            ax.axis('off')

    plt.show()  
    
def pictureVisBat(ddd,sho=True,save=False):
    import matplotlib.pylab as plt
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure(1, figsize=(10, 20))
    for j in range(len(ddd)):
            dd=np.asarray((ddd[j])).reshape(64,64,3)
            fig = plt.figure(1, figsize=(3, 3))
            ax = fig.add_subplot(8, 4, j+1)
            plt.imshow(dd,origin='upper')
            plt.axis('off')
    plt.show()
    
def volumeVisBat(ddd,th,name,sho=True,save=False):
    import matplotlib.pylab as plt
    from mpl_toolkits.mplot3d import Axes3D
    fig = plt.figure(1, figsize=(10, 20))
    for j in range(len(ddd)):
            dd=np.asarray((ddd[j]>th)).reshape(32,32,32)
            d=volume_to_3d(dd)
            fig = plt.figure(1, figsize=(3, 3))
            ax = fig.add_subplot(8, 4, j+1, projection='3d')
            ax.scatter(d[:, 0],d[:, 1],d[:, 2],s=1)
            ax.set_xlim(0,32)
            ax.set_ylim(0,32)
            ax.set_zlim(0,32)
            ax.axis('off')
    if save:
        
        fig.savefig(name+".png")
    if sho:
        plt.show()

    
def saveGenModel(shapeGenAll,labelAll,name):
    import scipy.io
    import pickle
    import numpy as np
    genAll = np.concatenate(shapeGenAll, axis=0)
    genAll = genAll.astype(np.uint8)
    labelAll = np.asarray(labelAll).astype(np.uint8)
    out = {"x": genAll, "y": labelAll}
    pickle.dump(out, open(name + ".pkl", "w"))
    out=pickle.load(open(name+".pkl", "r"))
    scipy.io.savemat(name, out)

    
def ImageToVector(x):
    # reuse flag
    reuse = len([t for t in tf.global_variables() if t.name.startswith('image_to_middle_vector')]) > 0
    with tf.sg_context(name='image_to_middle_vector', stride=2, act='relu', bn=True, reuse=reuse):
        tensor = x.sg_reshape(shape=(-1,24,137,137,3))
        tensor = tf.transpose(tensor, perm=[1,0,2,3,4])
        #only use one photo
        tensor = tf.random_shuffle(tensor)
        tensor = tensor[0]
        tensor = tensor.sg_reshape(shape=(-1, 137, 137, 3))
        ##############################################################
        dec1=tensor.sg_conv(dim=64, size=6, name='autoencoderImage11')
        dec2=dec1.sg_conv(dim=128, size=5, name='autoencoderImage12')
        dec3=dec2.sg_conv(dim=256, size=4, name='autoencoderImage13')
        tensor=dec3.sg_flatten()
        tensor = tensor.sg_dense(dim=100, name="autoencoderImage14", act='linear', bn=True)
    return tensor

###############################################################################################################
def GetAPClass(pred,real,label):
    data=np.concatenate((real,pred),axis=1)
    data=pd.DataFrame(data)
    data.columns=list(data.columns)[:-1]+["label"]
    rr=pd.concat((data.apply(lambda x: average_precision_score(np.asarray(x[:len(pred.T)]),np.asarray(x[(len(real.T)):])),
                          axis=1),pd.DataFrame(label)),axis=1)
    rr.columns=["AP","Class"]
    return (rr.groupby("Class").mean()).to_dict()


def GetIouClass(pred,real,label, iouThre):
    data=np.concatenate((real,pred),axis=1)
    data=pd.DataFrame(data)
    data.columns=list(data.columns)[:-1]+["label"]
    rr=pd.concat((data.apply(lambda x: CalculateIou(np.asarray(x[:len(pred.T)]),np.asarray(x[(len(real.T)):]), iouThre=iouThre),
                          axis=1),pd.DataFrame(label)),axis=1)
    rr.columns=["AP","Class"]
    return (rr.groupby("Class").mean()).to_dict()


def CalculateIou(input3DTestValue, genShapeFromImgTest, iouThre=0.2):

    toTest = genShapeFromImgTest
    # print 'Debug:', np.sum(genShapeFromImgTest), np.sum(input3DTestValue)
    # print np.sum(np.ones_like(input3DTestValue)[(input3DTestValue >= 0.99)])
    # print np.sum(np.ones_like(input3DTestValue)[(toTest >= iouThre)])
    intersect = np.sum(np.ones_like(input3DTestValue)[(input3DTestValue >= 0.99) & (toTest >= iouThre)])
    union = np.sum(np.ones_like(input3DTestValue)[(input3DTestValue >= 0.99) | (toTest >= iouThre)])
    iou = (intersect + 0.0) / union
    #print intersect, union, iou
    return iou

