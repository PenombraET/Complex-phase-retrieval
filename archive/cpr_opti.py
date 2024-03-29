import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
#import random

def random_complex_vector(length=1, distribution='gaussian', param=1/np.sqrt(2)):
    """
    Returns a complex vector of dimension length x 1
    If distribution=='gaussian', complex elements are as x+iy, with x,y ~N(0,param^2), param is std
    If distribution=='uniform', complex elements have norm ]0,param] uniformly randomly, phase ]0,2pi] uniformly randomly
    If distribution=='fixed_norm', complex elements have norm param, phase ]0,2pi] uniformly randomly
    If distribution=='real_gaussian', x ~N(0,param^2), param is std, y=0
    If distribution=='real_uniform', x has norm ]0,param] uniformly randomly, y=0

    Complex standard normal (gaussian) distribution has variance 1/2 over the real and over the imaginary part (total variance 1)
    The real one has 1
    """
    assert distribution in ['gaussian','uniform','fixed_norm','real_gaussian','real_uniform'], \
        f"Parameter distribution can not be {distribution}"

    if distribution=='gaussian':
        return np.random.normal(loc=0,scale=param,size=length) + \
            (0+1j)*np.random.normal(loc=0,scale=param,size=length)
    elif distribution=='fixed_norm':
        return param*np.exp(2*np.pi*(0+1j)*np.random.random(length))
    elif distribution=='uniform':
        return param*(1 - np.random.random(length))*np.exp(2*np.pi*(0+1j)*np.random.random(length)) #to have norm in ]0,param]
    elif distribution=='real_gaussian':
        return param*np.random.normal(loc=0,scale=param,size=length)
    elif distribution=='real_uniform':
        return param*(1 - np.random.random(length))*np.random.choice([-1,1],1)

def define_w_hat(dim,complex=True):
    """
    Returns a complex vector of dimension d x 1, the "teacher" vector to be found.
    Its components are randomly initialized: its norm is in [0,1[, its phase in [0,2pi[.
    Its complex norm squared is d (which means its numpy.linalg.norm is the root of d)

    If complex=False, returns a real vector of squared norm d
    """
    #assert isinstance(dim,int) and dim > 0, f"Given variable dim should not be {dim}"
    if complex:
        ret = random_complex_vector(dim,'uniform',1)
    else:
        ret = random_complex_vector(dim,'real_uniform',1)
    return np.sqrt(dim)*ret/np.linalg.norm(ret)

def define_X(n,d,law='gaussian',param=1/np.sqrt(2)):
    """
    Returns a matrix of dimension n x d, that is the data.
    If law=='gaussian', its rows are complex standard normally distributed, meaning x+iy with x,y~N(0,1/2)
    If law=='real_gaussian', its rows are standard normally distributed, meaning x+iy with x~N(0,1), y=0
    """

    return random_complex_vector(np.array([n,d]),law,param)

def define_y(X,w_hat):
    """
    Returns an array of dimension n x 1, built from the data X and the teacher vector w_hat
    It keeps only the modulus of every element, that should be in principle in [0,1]
    (but can be bigger if the dimension of w_hat is finite)
    """
    return np.abs(X@w_hat)/np.sqrt(len(w_hat))

def cost(h,h_0):
    """
    The cost function "mu", comparing |X^i@w| to the value y^i=|X^i@w_hat| it corresponds to, minimized in that value
    USELESS wait this function is useless
    """
    return (np.abs(h)**2-np.abs(h_0)**2)**2/2

def cost_der_1(h,h_0):
    """
    The derivative of the cost function "mu" in its first argument, h
    """
    return (np.abs(h)**2-np.abs(h_0)**2)*h.conj()

def isinbatch(b,n):
    """
    Gives a vector s_new with each element 1 with a probability b, or 0 otherwise.
    Vector of functions s^i(t)
    """
    s_new = np.random.choice(a=[1,0],p=[b,1-b],size=n)
    return s_new

def iterative_isinbatch(b,eta,tau,s_last):
    """
    The vector of functions s^i(t) when defined iteratively, takes its precedent state into account
    """

    prob_1 = eta/tau*(1-s_last) + (1-(1/b-1)*eta/tau)*s_last

    vec = np.random.random(len(s_last))
    
    return np.where(prob_1 > vec,1,0)

def loss(w,X,y,s_last,b):
    """
    The loss function to be minimized, y^i can be taken in place of \hat{h}^.
    
    """
    return np.sum(s_last/len(y)/b*cost(X@w/np.sqrt(len(w)),y))

def loss_grad(w,X,y,s_last,b):
    """
    The gradient in w of the loss function
    """

    ret = s_last.T@np.multiply(X.T,cost_der_1(X@w/np.sqrt(len(w)),y)).T/np.sqrt(len(w))/len(y)/b
    return (ret.T).conj()

def magnetization_norm(w,w_hat):
    return np.abs(w.conj().T@w_hat/len(w_hat))

def define_w_0(m_0, w_hat, complex=True):
    """
    The initialization of vector w, "warm initialization" to avoid getting stuck in a perpendicular
    state to w_hat
    """
    if complex:
        z = random_complex_vector(len(w_hat))
    else:
        z = random_complex_vector(len(w_hat),'real_gaussian',1)
    coeff = (-2*m_0*np.real(w_hat.T@np.conj(z)) + np.sqrt((2*m_0*np.real(w_hat.T@np.conj(z)))**2-z.T@np.conj(z)*len(w_hat)*(m_0**2-1)))/np.linalg.norm(z)**2
    vec = m_0*w_hat+coeff*z
    return vec/np.linalg.norm(vec)*np.sqrt(len(w_hat))

def w_next(w,X,y,b,eta,s_last):
    """
    The recursive algorithm that links all together
    """
    cal = w - eta*loss_grad(w,X,y,s_last,b)
    
    return cal/np.linalg.norm(cal)*np.sqrt(len(w))

def initialize(N, d, eta, tau, b, m_0, iter_max, isComplex):

    iter_max = int(iter_max)

    #eta must be smaller than tau
    #b must be bigger than eta/(tau+eta)

    assert eta <= tau, "eta must be smaller than tau"
    assert (b >= eta/(tau+eta)), "b must be bigger than eta/(tau+eta)"

    if isComplex:
        X = define_X(N,d,'gaussian')
    else:
        X = define_X(N,d,'real_gaussian',1)
    
    w_hat = define_w_hat(d,complex=isComplex)
    y = define_y(X,w_hat)

    m_norm_all = np.empty(iter_max)
    loss_all = np.empty(iter_max)
    s_vector = np.empty(N)
    w = define_w_0(m_0,w_hat,complex=isComplex)

    return X, w_hat, y, m_norm_all, loss_all, s_vector, w

def loop(N=100, d=30, eta=1, tau=10, b=0.1, m_0=0.2, iter_max=1e3, isComplex=True, np_rd_seed=None):

    np.random.seed(np_rd_seed)
    #random.seed(0) if actively using random

    X, w_hat, y, m_norm_all, loss_all, s_vector, w = initialize(N, d, eta, tau, b, m_0, iter_max, isComplex)

    iter_max = int(iter_max)
    
    s_vector = isinbatch(b,N) #to "initialize" s, actually havine s for t=0
    for iter in tqdm(range(iter_max)): #iteration is t
        m_norm_all[iter] = magnetization_norm(w,w_hat)
        loss_all[iter] = loss(w,X,y,s_vector,b)
        w = w_next(w,X,y,b,eta,s_vector)
        s_vector = iterative_isinbatch(b,eta,tau,s_vector) #"useless" on the last run but this way allows the prior isinbatch to be called for t=0

    return m_norm_all, loss_all


def plot_magLoss_iter(m_norm_all,loss_all,iter_max):

    plt.subplot(1,2,1)
    plt.plot(np.arange(0,iter_max,1),m_norm_all)
    plt.xlabel('t$/\eta$')
    plt.ylabel('|m|(t)')
    plt.xscale('log')
    plt.subplot(1,2,2)
    plt.plot(np.arange(0,iter_max,1),loss_all)
    plt.xlabel('t')
    plt.ylabel('$\mathcal{L}(t)$')
    plt.xscale('log')
    plt.yscale('log')
    plt.show()

def plot_descent_methods(m_norm, loss, labels, iter_max): #the m_norm and loss must be narrays of dim (diff_graphs, values)

    plt.subplot(1,2,1)
    plt.plot(np.arange(0,iter_max,1).T,m_norm.T,)
    plt.xlabel('t/$\eta$')
    plt.ylabel('|m|(t)')
    plt.xscale('log')
    plt.legend(labels)
    plt.subplot(1,2,2)
    plt.plot(np.arange(0,iter_max,1).T,loss.T)
    plt.xlabel('t')
    plt.ylabel('$\mathcal{L}(t)$')
    plt.xscale('log')
    plt.yscale('log')
    plt.legend(labels)
    plt.show()

def main_simple():

    N = 300
    d = 100
    eta = 0.01 # eta must be smaller than tau
    b = 0.5
    tau = 1 # b must be bigger than eta/(tau+eta)
    m_0 = 0.2
    iter_max = 1e5
    isComplex = False
    np_rd_seed = None # for the results to be reproductible


    save = False # True to run and save data, False to load data

    if not save:
        m_norm_all, loss_all = loop(N, d, eta, tau, b, m_0, iter_max, isComplex, np_rd_seed)
    else: #put it to True to save results
        data_graph = np.concatenate((m_norm_all,loss_all))
        np.savetxt("descent.csv", data_graph, fmt="%.6f")

        data_graph_ = np.genfromtxt('descent.csv')
        m_norm_all_ = data_graph[0:1]
        loss_all_ = data_graph[1:2]
        iter_max_ = len(m_norm_all)

    plot_magLoss_iter(m_norm_all, loss_all, iter_max)

def main_comparaison_methods():
    N = 3000
    d = 1000
    eta = 0.1 # eta must be smaller than tau
    b = np.array([1., 0.5, 0.5])
    tau = np.array([1., eta/0.5, 1.]) # b must be bigger than eta/(tau+eta)
    m_0 = 0.2
    iter_max = 1e3
    isComplex = True
    #np_rd_seed = np.arange(0,1,1) # for the results to be reproductible, the length of this object is the number of runs which get averaged
    np_rd_seed = np.random.randint(0,1000,1)

    graph_labels = ['GD','SGD','p-SGD']

    m_graph, loss_graph = np.empty((3,int(iter_max))), np.empty((3,int(iter_max)))

    print(f'N = {N}\nd = {d}\neta = {eta}\nb = {b}\ntau = {tau}\nm_0 = {m_0}\niter_max = {iter_max}\nisComplex = {isComplex}\nnb_samples_averaged = {len(np_rd_seed)}')

    for descent_type in range(3): # for each descent type, 500 different loops are taken over the narray np_rd_seed
        m_to_average, loss_to_average = np.empty((len(np_rd_seed),int(iter_max))), np.empty((len(np_rd_seed),int(iter_max)))
        print(f'Beginning method {descent_type} --------------')
        for sample in range(len(np_rd_seed)):
            print(f'Beginning the {sample}th sample --------------')
            m_to_average[sample], loss_to_average[sample] = loop(N, d, eta, tau[descent_type], b[descent_type], m_0, iter_max, isComplex, np_rd_seed[sample])
        m_graph[descent_type], loss_graph[descent_type] = np.mean(m_to_average,axis=0), np.mean(loss_to_average,axis=0)

    data_graph = np.concatenate((m_graph,loss_graph))

    np.savetxt(f"methods_comparaison_iter_1e6_complex_{isComplex}_d{d}_eta001.csv", data_graph, fmt="%.6f")

    #data_graph = np.genfromtxt('methods_comparaison.csv')
    #m_graph = data_graph[0:3]
    #loss_graph = data_graph[3:6]

    #data_graph_d100 = np.genfromtxt('methods_comparaison_d100.csv')
    #m_graph_d100 = data_graph_d100[0:3]
    #loss_graph_d100 = data_graph_d100[3:6]
    #graph_labels_d100 = ['GD d100', 'SGD d100', 'p-SGD d100']

    #plot_descent_methods(np.concatenate((m_graph,m_graph_d100)), np.concatenate((loss_graph,loss_graph_d100)), graph_labels+graph_labels_d100, int(iter_max))

    #plot_descent_methods(m_graph, loss_graph, graph_labels, int(iter_max))

def main_plot_comparaison():
    data_graph = np.genfromtxt('methods_comparaison_iter_1e3_complex_True_d1000_eta01.csv')
    m_graph = data_graph[0:3]
    loss_graph = data_graph[3:6]
    iter_max = len(m_graph[0])
    graph_labels = ['GD','SGD','p-SGD']
    plot_descent_methods(m_graph, loss_graph, graph_labels, int(iter_max))

def main_to_plot():
    data_graph_d100 = np.genfromtxt('methods_comparaison_d100.csv')
    m_graph_d100 = data_graph_d100[0:3]
    loss_graph_d100 = data_graph_d100[3:6]
    graph_labels_d100 = ['GD d100', 'SGD d100', 'p-SGD d100']

    data_graph = np.genfromtxt('methods_comparaison_d200.csv')
    m_graph = data_graph[0:3]
    loss_graph = data_graph[3:6]
    graph_labels = ['GD', 'SGD', 'p-SGD']
    
    iter_max = 1e3

    plot_descent_methods(np.concatenate((m_graph,m_graph_d100)), np.concatenate((loss_graph,loss_graph_d100)), graph_labels+graph_labels_d100, int(iter_max))


if __name__ == "__main__":
    #main_comparaison_methods()
    main_plot_comparaison()
    #main_simple()