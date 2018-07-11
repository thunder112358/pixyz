import torch

from ..utils import get_dict_values


class KullbackLeibler(object):
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2

        self.p1_name = self.p1.distribution_name
        self.p2_name = self.p2.distribution_name

    def estimate(self, x):
        if self.p1_name == "Normal" and self.p2_name == "Normal":
            inputs = get_dict_values(x, self.p1.cond_var, True)
            params1 = self.p1.get_params(**inputs)

            inputs = get_dict_values(x, self.p2.cond_var, True)
            params2 = self.p2.get_params(**inputs)

            return gauss_gauss_kl(params1["loc"], params1["scale"],
                                  params2["loc"], params2["scale"])

        raise Exception("You cannot use these distributions, "
                        "got %s and %s." % (self.p1_name,
                                            self.p2_name))


def gauss_gauss_kl(loc1, scale1, loc2, scale2):
    _kl = torch.log(scale2) - torch.log(scale1) \
            + (scale1 + (loc1 - loc2)**2) / scale2 - 1
    return 0.5 * torch.sum(_kl, dim=1)
