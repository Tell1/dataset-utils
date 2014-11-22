"""
.. module:: fhmm
   :platform: Unix
   :synopsis: Contains methods for training and fitting Factorials HMMs.

.. moduleauthor:: Phil Ngo <ngo.phil@gmail.com>
.. moduleauthor:: Miguel Perez <miguel.a.perez4@gmail.com>
.. moduleauthor:: Stephen Suffian <stephen.suffian@gmail.com>
.. moduleauthor:: Sabina Tomkins <sabina.tomkins@gmail.com>

"""

from sklearn import hmm
import utils
from copy import deepcopy
import numpy as np
import pandas as pd
from collections import OrderedDict
import itertools
import matplotlib.pyplot as plt
import json

def init_HMM(pi_prior,a_prior,mean_prior,cov_prior):
    '''
    Initializes a trace object from a series and a metadata dictionary.
    Series must be sampled at a particular sample rate
    pi_prior is the starting probability of the HMM
    a_prior is the transition matrix of the HMM
    mean_prior is the initial mean value of each state
    cov_prior is the initial covariance of each state

    For an n-state HMM:

    * pi_prior is a 1-D numpy array of size n
    * a_prior is a 2-D numpy array of size n x n
    * mean_prior is an numpy array of size n
    * cov_prior is a 3-D numpy array that has been tiled into two rows,
      one column, and n third dimensional states.

      * ex) np.tile(1,(2,1,n)) for uniform covariance to start with.
    '''
    model = hmm.GaussianHMM(pi_prior.size,'full',pi_prior,a_prior)
    model.means_ = mean_prior
    model.covars_ = cov_prior
    return model

def fit_trace_to_HMM(model,trace):
    '''
    Fits the given trace to the model. NaNs are turned into zeroes.
    '''
    trace_values = utils.trace_series_to_numpy_array(trace.series)
    model.fit([trace_values])
    startprob, means, covars, transmat = _sort_learnt_parameters(model.startprob_,
            model.means_, model.covars_ , model.transmat_)
    model=hmm.GaussianHMM(startprob.size, 'full', startprob, transmat)
    model.means_ = means
    model.covars_ = covars
    return model

def fit_instance_to_HMM(model,instance):
    '''
    Fits the given instance to the model. NaNs are turned into zeroes.
    '''
    for trace in instance.traces:
        model=fit_trace_to_HMM(model,trace)
    return model

def generate_HMMs_from_type(type,pi_prior,a_prior,
        mean_prior,cov_prior,key_for_model_name=None):
    '''
    Generates a dictionary of HMMs using each instance of given type.
    The key to the dictionary is defined by the parameter 'key_for_model_name'
    which looks at each instances metadata and uses the value from that key
    in order to name the model. If no key is given, the model is named based on
    its index.
    '''
    instance_models=OrderedDict()
    for i,instance in enumerate(type.instances):
        if(key_for_model_name):
            instance_name=instance.traces[0].metadata[key_for_model_name]
        else:
            instance_name=i
        instance_models[instance_name]=init_HMM(pi_prior,a_prior,mean_prior,cov_prior)
        instance_models[instance_name]=fit_instance_to_HMM(instance_models[instance_name],
                instance)
    return instance_models

def generate_FHMM_from_HMMs(type_models):
    '''
    Takes a dictionary of models, where the keys are the device type name, and
    generates an FHMM of these models. It returns the fhmm model as well as 
    a dictionary with the key being device type and each value being a list
    containing the means for each state of that device type.
    '''
    list_pi=[]
    list_A=[]
    list_means=[]
    means={}
    variances={}
    for device_type_name in type_models:
        list_pi.append(type_models[device_type_name].startprob_)
        list_A.append(type_models[device_type_name].transmat_)
        list_means.append(type_models[device_type_name].means_.flatten().
            tolist())
        means[device_type_name]=type_models[device_type_name].means_
        variances[device_type_name]=type_models[device_type_name].covars_
    pi_combined=_compute_pi_fhmm(list_pi)
    A_combined=_compute_A_fhmm(list_A)
    [mean_combined, cov_combined]=_compute_means_fhmm(list_means)
    model_fhmm=_create_combined_hmm(len(pi_combined),pi_combined,
            A_combined, mean_combined, cov_combined)
    return model_fhmm,means,variances

def predict_with_FHMM(model_fhmm,means,variances,power_total):
    '''
    Predicts the _decoded states and power for the given test data with the
    given FHMM. test_data is a dictionary containing keys for each device
    that is in the FHMM.
    '''
    learnt_states=model_fhmm.predict(power_total)
    [_decoded_states,_decoded_power]=_decode_hmm(len(learnt_states), means,
            variances, means.keys(), learnt_states)
    np.putmask(_decoded_power['air1'],_decoded_power['air1'] >= power_total.T,
             power_total.T)
    return _decoded_states,_decoded_power

def predict_with_FHMM_temp(model_fhmm,means,variances,power_temp_total):
    '''
    Predicts the _decoded states and power for the given test data with the
    given FHMM. test_data is a dictionary containing keys for each device
    that is in the FHMM.
    '''
    learnt_states=model_fhmm.predict(power_total)
    [_decoded_states,_decoded_power]=_decode_hmm(len(learnt_states), means,
            variances, means.keys(), learnt_states)
    np.putmask(_decoded_power['air1'],_decoded_power['air1'] >= power_total.T,
             power_total.T)
    return _decoded_states,_decoded_power
def plot_FHMM_and_predictions(test_data,_decoded_power):
    '''
    This plots the actual and predicted power based on the FHMM.
    '''
    for i,device_type in enumerate(test_data):
        if(device_type is not 'use'):
            plt.figure()
            plt.plot(test_data[device_type],'g')
            plt.plot(_decoded_power[device_type],'b')
            plt.title('Ground Truth (Green) and Predicted (Blue) for %s' %device_type)
            plt.ylabel('Power (W)')
            plt.xlabel('Time')
            plt.ylim((np.min(test_data[device_type])-10, np.max(test_data[device_type])+10))
            plt.tight_layout()

def get_best_instance_model(instance_models,device_type,key_for_model_name):
    dfs_model = {}
    best_model_score = 0
    for model_name in instance_models:
        instances_of_model = []
        for instance in device_type.instances:
            test_trace = instance.traces[0]
            instance_name = test_trace.metadata[key_for_model_name]
            test = utils.trace_series_to_numpy_array(test_trace.series)
            model_score = instance_models[model_name].score(test)
            instances_of_model.append([model_name,instance_name,model_score])
            if(model_score > best_model_score):
                best_model = instance_models[model_name]
        dfs_model[model_name] = pd.DataFrame(data=instances_of_model,
                columns=['Model_Instance','Test_Instance','Value'])
    model_averages = []
    for key in dfs_model:
        sum=0
        for row in dfs_model[key].iterrows():
            sum = sum+row[1]['Value']
        model_averages.append([key,sum/len(dfs_model[key].index)])
    print
    avg_model_df = pd.DataFrame(data=model_averages,
            columns=['Model_Instance','Avg Probability'])
    print avg_model_df._sort('Avg Probability',ascending=False)
    bestModel = avg_model_df._sort('Avg Probability',
            ascending=False)._sort('Avg Probability',
                    ascending=False).head(1)['Model_Instance'].values[0]
    print str(bestModel) + ' is best.'
    return bestModel

def _sort_startprob(mapping, startprob):
    '''
    _sort the startprob of the HMM according to power means; as returned by mapping
    '''

    num_elements = len(startprob)
    new_startprob = np.zeros(num_elements)
    for i in xrange(len(startprob)):
        new_startprob[i] = startprob[mapping[i]]
    return new_startprob

def _sort_covars(mapping, covars):
    num_elements = len(covars)
    new_covars = np.zeros_like(covars)
    for i in xrange(len(covars)):
        new_covars[i] = covars[mapping[i]]
    return new_covars

def _sort_transition_matrix(mapping, A):
    '''
    sorts the transition matrix of the HMM according to power means; as returned by mapping
    '''
    num_elements = len(A)
    A_new = np.zeros((num_elements, num_elements))
    for i in range(num_elements):
        for j in range(num_elements):
            A_new[i,j] = A[mapping[i], mapping[j]]
    return A_new

def _return_sorting_mapping(means):
    means_copy = deepcopy(means)
    # _sorting
    means_copy = np.sort(means_copy, axis = 0)
    # Finding mapping
    mapping = {}
    mapping_set=set()
    x=0
    for i, val in enumerate(means_copy):
        x= np.where(val==means)[0]
        for val in x:
            if val not in mapping_set:
                mapping_set.add(val)
                mapping[i]=val
                break
    return mapping

def _sort_learnt_parameters(startprob, means, covars, transmat):
    '''
    sorts the learnt parameters for the HMM
    '''
    mapping = _return_sorting_mapping(means)
    means_new = np.sort(means, axis = 0)

    startprob_new = _sort_startprob(mapping, startprob)
    covars_new = _sort_covars(mapping, covars)
    transmat_new = _sort_transition_matrix(mapping, transmat)
    assert np.shape(means_new) == np.shape(means)
    assert np.shape(startprob_new) == np.shape(startprob)
    assert np.shape(transmat_new) == np.shape(transmat)
    return [startprob_new, means_new, covars_new, transmat_new]

def _compute_pi_fhmm(list_pi):
    '''
    Input: list_pi: List of PI's of individual learnt HMMs
    Output: Combined Pi for the FHMM
    '''
    result=list_pi[0]
    for i in range(len(list_pi)-1):
        result=np.kron(result,list_pi[i+1])
    return result

def _compute_A_fhmm(list_A):
    '''
    Input: list_pi: List of PI's of individual learnt HMMs
    Output: Combined Pi for the FHMM
    '''
    result=list_A[0]
    for i in range(len(list_A)-1):
        result=np.kron(result,list_A[i+1])
    return result

def _compute_means_fhmm(list_means):  
    '''
    Returns [mu, sigma]
    '''

    #list_of_appliances_centroids=[ [appliance[i][0] for i in range(len(appliance))] for appliance in list_B]
    states_combination=list(itertools.product(*list_means))
    num_combinations=len(states_combination)
    means_stacked=np.array([sum(x) for x in states_combination])
    means=np.reshape(means_stacked,(num_combinations,1))
    cov=np.tile(5*np.identity(1), (num_combinations, 1, 1))
    return [means, cov]

def _create_combined_hmm(n, pi, A, mean, cov):
    combined_model=hmm.GaussianHMM(n_components=n,covariance_type='full', startprob=pi, transmat=A)
    combined_model.covars_=cov
    combined_model.means_=mean
    return combined_model

def _decode_hmm(length_sequence, centroids, variance, appliance_list, states):
    '''
    decodes the HMM state sequence
    '''
    power_states_dict={}
    hmm_states={}
    hmm_power={}
    total_num_combinations=1
    for appliance in appliance_list:
        total_num_combinations*=len(centroids[appliance])

    for appliance in appliance_list:
        hmm_states[appliance]=np.zeros(length_sequence,dtype=np.int)
        hmm_power[appliance]=np.zeros(length_sequence)

    for i in range(length_sequence):
        factor=total_num_combinations
        for appliance in appliance_list:
            #assuming integer division (will cause errors in Python 3x)
            factor=factor//len(centroids[appliance])

            temp=int(states[i])/factor
            hmm_states[appliance][i]=temp%len(centroids[appliance])
            mu=centroids[appliance]
            sigma=variance[appliance]
            hmm_power[appliance][i]=np.array([0,np.random.normal(mu[1],sigma[1],
                1)[0]]).reshape(2,1)[hmm_states[appliance][i]]
    return [hmm_states,hmm_power]


def disaggregate_data(model_tuple, trace):
    data=[]
    power_total=utils.trace_series_to_numpy_array(trace.series)
    [decoded_states, decoded_power]=predict_with_FHMM(model_tuple[0],
            model_tuple[1],model_tuple[2],power_total)
    for i,v in enumerate(decoded_power['air1']):
        date_time=trace.series.index[i]
        value=trace.series[i]
        data.append({'date':date_time.strftime('%Y-%m-%d %H:%M'),
            'dg': float(v),'reading':float(value)})
    json_string = json.dumps(data, ensure_ascii=False,indent=4,
            separators=(',', ': '))
    return json_string

def get_simple_fhmm(means,ons,offs,pis,covs_on,covs_off):
    hmms = {}
    for i,(mean,on,off,cov_on,cov_off,pi) in enumerate(zip(means,ons,offs,covs_on,covs_off,pis)):
        pi_prior = np.array([1 - pi,pi])
        a_prior = np.array([[off, 1 - off],[1 - on,on]])
        mean_prior = np.array([0,mean])[:,np.newaxis]
        cov_prior = np.array([cov_on,cov_off])[:,np.newaxis,np.newaxis]
        hmms["device_{}".format(i)] = init_HMM(pi_prior,a_prior,mean_prior,cov_prior)
    appliance_hmm,_,_ = generate_FHMM_from_HMMs(hmms)
    return appliance_hmm

def get_states(individual_means,appliance_fhmm,use):
    states = appliance_fhmm.predict(use)
    combinations = _get_combinations(individual_means.shape[0])
    state_means = []
    for combo in combinations:
        state_means.append(np.sum(individual_means * combo))
    decoded_state_key = sorted(zip(state_means,combinations), key = lambda x: x[0])
    decoded_states = [decoded_state_key[state][1] for state in states]
    return np.array(decoded_states)

def _get_combinations(n):
    combos = []
    for i in range(2**n):
        combo = []
        for j in range(n-1,-1,-1):
            combo.append(int(2**j<=i))
            if 2**j <= i:
                i = i - 2**j
        combos.append(combo)
    return np.array(combos)
