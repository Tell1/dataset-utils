#Wikienergy Deep Dive 1

-----

#####[Goals](#principal-goals) | [Data Sources](#data-sources) | [Algorithms](#algorithms) | [Analysis](#analysis)

</br>

-----

##Principal Goals
  - Create a tool for evaluating energy-saving interventions
  - Create an accurate energy disaggregator (15 minutes)

-----

##Data Sources
[Pecan Street](#pecan-street) | [Tracebase](#tracebase) |
[Weather](#weather) | [Oak Park](#oak-park)

###Pecan Street

####Overview
- 23 cities
- disaggregated ground truth
- ~70 unique appliances
  - 8-20 typical per house
- professional audit and survey data
  - city
  - type of insulation
  - type of HVAC

####Curated Dataset
- Austin, TX
- 75 households
- January-November 2013
- 15 minute intervals

####Raw Dataset
- 577 households
- 15 minute and 1 minute

####Shared Dataset
- 200 households
- January-April 2014
- 1 minute intervals

###Tracebase
- 24-hour, 1-second data for 43 unique appliances
- up to 200 traces per appliance
- from TU Darmstadt, Germany

###Weather
- historical and live hourly interval weather data
- source: wunderground

###Oak Park
- 15 minute (possibly 1 minute)
- green button API
- LIVE!!

-----

##Algorithms
[Hidden Markov Model](#hidden-markov-model-hmm) |
[Factorial Hidden Markov Model](#factorial-hidden-markov-model-fhmm) |
[Neural Networks](#neural-networks)

###Goals

####Disaggregation

- Existence
- Modeling Appliances
- Labeling States
- Extracting Signal

###Hidden Markov Model (HMM)

-  Develop appliance instance parameters using hidden markov models
    *   z<sub>t</sub>(discrete variable) corresponds to one of K states
(state1=on, state2=off)
    *   x<sub>t</sub> (continous variable) is amount of power > 0 (e.x. 100 W)
    *   Hidden Markov Parameters:
        *   Initial Probabilities (&alpha;)
        *   Transition matrix (C) (probability of transition between hidden
states)
        *   Emission variables (&phi;) – Gaussian-Gamma, hyperparameters:
            *   mean, precision, shape, scale
        *   Observed Data (power values, other features)
        *   Hidden States (ON or OFF)
    *  Can be used to generate sample data, predict states, evaluate likelihood
    *  Often used for modeling probabalistic temporal processes
    *  Limited ability to model periodic signals

![Hidden Markov Model Image](../../assets/images/bayesianhiddenmarkov.png)


###Factorial Hidden Markov Model (FHMM)
*  combines several hidden markov models in parallel
*   state space comprises all possible combinations of appliance states

###Neural Networks
* Used for semi-supervised and supervised learning
* Good for modeling non-linear functions
* Mimics biological neurons
* Multiple layers of neurons
* Each neuron applies a sigmoidal function to the weighted sum of the
activations of its input neurons
![Neural Network](../../assets/images/neuralnetworks.png)

###Accomplishments
* Made HMM appliance models using Tracebase data
* Made training data for FHMMs using appliance models

####Aggregated Power Signal

<img src="../../assets/images/aggpower.png" height=300 width = 900 >
####Disaggregated Stove Power Signal (Real and Estimated)
<img src="../../assets/images/disaggstove.png" height=300 width = 900 >
####Disaggregated Refrigerator Power Signal (Real and Estimated)
<img src="../../assets/images/disaggref.png" height=300 width = 900 >

* Disaggregated Tracebase test data
* Used HMM models to train a neural network

###Challenges
* Detecting appliance existence
* Encoding time in FHMMs
* Understand Step Variant Convolutional Neural Networks

-----

##Analysis
###Most Common Appliances in Homes
* Ask for suggestions

###Percent HVAC
Historically, heating, ventilation, and air conditioning have consumed over
half of all home energy. Nationwide the fraction of energy consumed by HVAC
has gone down from 58% in 1993 to 48% in 2009, but the number is still large.
In intense climates the percent used by HVAC can be even larger, in research
done by Pecan Street HVAC demanded 82% of the energy of some homes.
Here is what we found:


<img src="../../assets/images/Percent_Hvac_03.png" width=33% alt = "March">
<img src="../../assets/images/Percent_Hvac_07.png" width=33% alt = "July">
<img src="../../assets/images/Percent_Hvac_10.png" width=33% alt = "October">


###Weather
* Sanity check for Heat and AC use, by looking at correlation
* Created an API which returns minute interval weather data(temp) by zip code
    * This allows us to embed weather information in future models 

####Usage
Use `get_weather_data(api_key,city,state,start_date,end_date)` to query historical weather data. The function will return a JSON object. To query live weather data, use `get_current_temp(city,state, zipcode = None)`.
####January Temperature
<img src="../../assets/images/January_Weather.png" height=300 width = 900 >

####January AC Usage
<img src="../../assets/images/ac_01.png" height=300 width = 900 >

####April Temperature
<img src="../../assets/images/April_Weather.png" height=300 width = 900 >

####April AC Usage
<img src="../../assets/images/ac_04.png" height=300 width = 900 >

####July Temperature
<img src="../../assets/images/July_Weather.png" height=300 width = 900 >

####July AC Usage
<img src="../../assets/images/ac_07.png" height=300 width = 900 >

####October Temperature
<img src="../../assets/images/October_Weather.png" height=300 width = 900 >

####October AC Usage
<img src="../../assets/images/ac_10.png" height=300 width = 900 >

###EV
After speaking with Pecan Street we learned that there is need for a way to reliably classify an electric vehicle opposed to another large load, such as HVAC. We've started exploring the homes with EV data looking for the signatures of these cars. 

#####Daily Signature over Four Months
![Daily Signature over Four Months](../../assets/images/2014-EV.png)
#####Daily Signature over One Day
![Daily Signature over One Day](../../assets/images/day_ev_charge_1.png)

![Daily Signature over One Day](../../assets/images/day_ev_charge_6.png)

![Daily Signature over One Day](../../assets/images/day_ev_charge_20.png)
