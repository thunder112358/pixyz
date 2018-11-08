# Pixyz: a library for developing deep generative models

![logo](https://user-images.githubusercontent.com/11865486/47983581-31c08c80-e117-11e8-8d9d-1efbd920718c.png)


[![Python Version](https://img.shields.io/pypi/pyversions/Django.svg)](https://github.com/masa-su/pixyz)

## What is Pixyz?
Pixyz is developed to implement various kind of deep generative models, which is based on [PyTorch](https://pytorch.org/).

Recently, many papers on deep generation models have been published. However, it is likely to be difficult to reproduce them with codes as there is a gap between mathematical formulas presented in these papers and actual implementation of them. Our objective is to create a new library which enables us to fill this gap and easy to implement these models. With Pixyz, you can implement even more complicated models **just as if writing these formulas**, as shown below.

Our library supports following typical deep generative models.

* Explicit models (likelihood-based)
  * variational autoencoders (variational inference)
  * flow-based models
* Implicit models
  * generative adversarial networks

## Installation
```
$ git clone https://github.com/masa-su/pixyz.git
$ pip install -e pixyz --process-dependency-links
```

## Quick Start

So now, let's create a deep generative model with Pixyz! Here, we consider to implement a variational auto-encoder (VAE) which is one of the most well-known deep generative models. VAE is composed of a inference model q(z|x) and a generative model p(x,z)=p(x|z)p(z), which are defined by DNNs, and this objective function is as follows.

<img src="https://latex.codecogs.com/gif.latex?E_{q_\phi(z|x)}[\log&space;\frac{p_\theta(x,z)}{q_\phi(z|x)}]&space;\leq&space;\log&space;p(x)" />

### 1, Define the distributions
First, we need to define two distributions, q(z|x), p(x|z), with DNNs. In Pixyz, you can do this by implementing DNN architectures just as you do with PyTorch. The main difference is that we should write a class which inherits the `pixyz.distributions.*` class (**Distribution API**), not the `torch.nn.Module` class.

For example, p(x|z) (Bernoulli) and q(z|x) (Normal) can be defined as follows.

```python
from pixyz.distributions import Bernoulli, Normal
# inference model q(z|x)
class Inference(Normal):
    def __init__(self):
        super(Inference, self).__init__(cond_var=["x"], var=["z"], name="q")        

        self.fc1 = nn.Linear(784, 512)
        self.fc2 = nn.Linear(512, 512)
        self.fc31 = nn.Linear(512, 64)
        self.fc32 = nn.Linear(512, 64)

    def forward(self, x):
        h = F.relu(self.fc1(x))
        h = F.relu(self.fc2(h))
        return {"loc": self.fc31(h), "scale": F.softplus(self.fc32(h))}

    
# generative model p(x|z)    
class Generator(Bernoulli):
    def __init__(self):
        super(Generator, self).__init__(cond_var=["z"], var=["x"], name="p")

        self.fc1 = nn.Linear(64, 512)
        self.fc2 = nn.Linear(512, 512)
        self.fc3 = nn.Linear(512, 128)

    def forward(self, z):
        h = F.relu(self.fc1(z))
        h = F.relu(self.fc2(h))
        return {"probs": F.sigmoid(self.fc3(h))}
```
Once defined, we can create these instances from them. 
```python
p = Generator()
q = Inference()
```

If you want to use distributions which don't need to be defined with DNNs, you just create new instance from `pixyz.distributions.*`. In VAE, p(z) is usually defined as the standard normal distribution.
```python
loc = torch.tensor(0.)
scale = torch.tensor(1.)
prior = Normal(loc=loc, scale=scale, var=["z"], dim=64, name="p_prior")
```

If you want to see what kind of distribution and architecture each instance defines, just `print` them!
```python
print(p)
>> Distribution:
>>   p(x|z) (Bernoulli)
>> Network architecture:
>>   Generator(
>>     (fc1): Linear(in_features=64, out_features=512, bias=True)
>>     (fc2): Linear(in_features=512, out_features=512, bias=True)
>>     (fc3): Linear(in_features=512, out_features=784, bias=True)
>> )
```
Conveniently, each instance (distribution) can **perform sampling** and **estimate (log-)likelihood** given samples regardless of the form of the internal DNN architecture. It will be explained later (see section 2.3).

Moreover, in VAE, we should define the joint distribution p(x,z)=p(x|z)p(z) as the generative model. In **Distribution API**, you can directly calculate the product of different distributions!
```python
p_joint = p * prior
print(p_joint)
>> Distribution:
>>   p(x,z) = p(x|z)p_prior(z)
>> Network architecture:
>>   p_prior(z) (Normal): Normal()
>>   p(x|z) (Bernoulli): Generator(
>>    (fc1): Linear(in_features=64, out_features=512, bias=True)
>>    (fc2): Linear(in_features=512, out_features=512, bias=True)
>>    (fc3): Linear(in_features=512, out_features=784, bias=True)
>>  )
```
This distribution can also perform sampling and likelihood estimation in the same way. Thanks to this API, we can easily implement even more complicated probabilistic models.

### 2. Set objective function and train the model
After defining distributions, we should set the objective fuction of the model and train (optimize) it. In Pixyz, there are three ways to do this.

1. Model API
2. Loss API
3. Using only Distribution API

We can choose either of these three ways, but upper one is for beginners and lower is for developers/researchers.

#### 2.1. Model API
The simplest way to create trainable models is to use Model API (`pixyz.models.*`). Our goal in this tutorial is to implement the VAE, so we choose `pixyz.models.VI` (which is for variational inference) and set distributions defined above and the optimizer.
```python
from pixyz.models import VI
model = VI(p_joint, q, optimizer=optim.Adam, optimizer_params={"lr":1e-3})
```
Mission complete! To train this model, simply run the `train` method with data as input.
```python
loss = model.train({"x": x_tensor}) # x_tensor is torch.Tensor
```

In addition to VI, we prepared various models for Model API such as GAN, VAE (negative reconstruction error + KL), ML etc.

#### 2.2. Loss API
In general case, we simply use Model API. But how about this case?

<img src="https://latex.codecogs.com/gif.latex?\sum_{x,y&space;\sim&space;p_{data}(x,&space;y)}&space;\left[E_{q(z|x,y)}\left[\log&space;\frac{p(x,z|y)}{q(z|x,y)}\right]&space;&plus;&space;\alpha&space;\log&space;q(y|x)\right]&space;&plus;&space;\sum_{x_u&space;\sim&space;p_{data}(x_u)}\left[E_{q(z|x_u,y)q(y|x_u)}\left[\log&space;\frac{p(x_u,z|y)}{q(z|x_u,y)q(y|x_u)}\right]\right]" /> (2)

This is the loss function of semi-supervised VAE [Kingma+ ]. It seems that it is too complicated to implement by Model API. 

**Loss API** enables us to implement such complicated models as if just writing mathmatic formulas. If we have already define distributions which appear in Eq.(2) by Distribution API, we can easily convert Eq.(2) to the code style with `pixyz.losses.*` as follows.
```python
from pixyz.losses import ELBO, NLL
# The defined distributions are p_joint_u, q_u, p_joint, q, f.
elbo_u = ELBO(p_joint_u, q_u)
elbo = ELBO(p_joint, q)
nll = NLL(f)

loss_cls = -elbo_u.sum() - (elbo - (0.1 * nll)).sum()
```
We can check what formal this loss is just by printing!
```python
print(loss_cls)
>> -(sum(E_p(z,y_u|x_u)[log p(x_u,z|y_u)/p(z,y_u|x_u)])) - sum(E_q(z|x,y)[log p(x,z|y)/q(z|x,y)] - log p(y|x) * 0.1)
```
When you want to estimate a value of the loss function given data, you can use `estimate` method.
```python
loss_tensor = loss_cls.estimate({"x": x_tensor, "y": y_tensor, "x_u": x_u_tensor})
print(loss_tensor)
>> tensor(1.00000e+05 *
          1.2587, device='cuda:0')
```
This value is a

#### 2.3. Using only Distribution API



