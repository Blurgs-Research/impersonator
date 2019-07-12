import os
import torch
from torch.optim import lr_scheduler
from collections import OrderedDict

from networks.bodymesh.mesh import get_map_fn_dim


class ModelsFactory(object):
    def __init__(self):
        pass

    @staticmethod
    def get_by_name(model_name, *args, **kwargs):
        model = None

        is_train = args[0].is_train
        if model_name == 'background_inpaintor':
            if is_train:
                from models.background import InpaintorTrainer
                model = InpaintorTrainer(*args, **kwargs)
            else:
                from models.background import Inpaintor
                model = Inpaintor(*args, **kwargs)

        elif model_name == 'imper_v2':
            from models.trainer_imper_v2 import ImperTrainer
            model = ImperTrainer(*args, **kwargs)

        elif model_name == 'imper_v2_fixbg':
            from models.trainer_imper_v2 import ImperTrainerFixBG
            model = ImperTrainerFixBG(*args, **kwargs)

        elif model_name == 'imper_v2_fixbg_imitator':
            from models.trainer_imper_v2 import Imitator
            model = Imitator(*args, **kwargs)

        elif model_name == 'concat':
            from models.trainer_baselines import ConcatTrainer
            model = ConcatTrainer(*args, **kwargs)

        elif model_name == 'texture':
            from models.trainer_baselines import TextureWarpingTrainer
            model = TextureWarpingTrainer(*args, **kwargs)

        elif model_name == 'feature':
            from models.trainer_baselines import FeatureWarpingTrainer
            model = FeatureWarpingTrainer(*args, **kwargs)

        elif model_name == 'impersonator':
            from models.impersonator import ImpersonatorTrainer
            # from models.impersonator import Impersonator
            model = ImpersonatorTrainer(*args, **kwargs)

        else:
            raise ValueError("Model %s not recognized." % model_name)

        print("Model %s was created" % model.name)
        return model


class BaseModel(object):

    def __init__(self, opt):
        self._name = 'BaseModel'

        self._opt = opt
        self._gpu_ids = opt.gpu_ids
        self._is_train = opt.is_train

        self._Tensor = torch.cuda.FloatTensor if self._gpu_ids else torch.Tensor
        self._save_dir = os.path.join(opt.checkpoints_dir, opt.name)

        self._G_cond_nc, self._D_cond_nc = self.cond_nc()

    @property
    def name(self):
        return self._name

    @property
    def is_train(self):
        return self._is_train

    def cond_nc(self):
        if self._opt.map_name:
            nc = get_map_fn_dim(self._opt.map_name)
            # _G_cond_nc, _D_cond_nc = nc, nc + nc
            _G_cond_nc, _D_cond_nc = nc, nc
        else:
            _G_cond_nc = self._opt.cond_nc
            _D_cond_nc = self._opt.cond_nc

        return _G_cond_nc, _D_cond_nc

    def _load_network(self, network, network_label, epoch_label, need_module=False):
        load_filename = 'net_epoch_%s_id_%s.pth' % (epoch_label, network_label)
        load_path = os.path.join(self._save_dir, load_filename)

        self._load_params(network, load_path, need_module)

    def _load_params(self, network, load_path, need_module=False):
        assert os.path.exists(
            load_path), 'Weights file not found. Have you trained a model!? We are not providing one %s' % load_path

        def load(model, orig_state_dict):
            state_dict = OrderedDict()
            for k, v in orig_state_dict.items():
                if 'module' in k:
                    name = k[7:]  # remove `module.`
                else:
                    name = k
                state_dict[name] = v

            # load params
            model.load_state_dict(state_dict)

        save_data = torch.load(load_path)
        if need_module:
            network.load_state_dict(save_data)
        else:
            load(network, save_data)
        print('loaded net: %s' % load_path)


class BaseTrainerModel(BaseModel):

    def __init__(self, opt):
        super(BaseTrainerModel, self).__init__(opt=opt)

        self._name = 'BaseTrainerModel'

    def cond_nc(self):
        if self._opt.map_name:
            nc = get_map_fn_dim(self._opt.map_name)
            _G_cond_nc, _D_cond_nc = nc, nc
        else:
            _G_cond_nc = self._opt.cond_nc
            _D_cond_nc = self._opt.cond_nc

        return _G_cond_nc, _D_cond_nc

    def set_input(self, input):
        assert False, "set_input not implemented"

    def set_train(self):
        assert False, "set_train not implemented"

    def set_eval(self):
        assert False, "set_eval not implemented"

    def forward(self, *input):
        assert False, "forward not implemented"

    # used in test time, no backprop
    def test(self):
        assert False, "test not implemented"

    def get_image_paths(self):
        return {}

    def optimize_parameters(self):
        assert False, "optimize_parameters not implemented"

    def get_current_visuals(self):
        return {}

    def get_current_errors(self):
        return {}

    def get_current_scalars(self):
        return {}

    def save(self, label):
        assert False, "save not implemented"

    def load(self):
        assert False, "load not implemented"

    def _save_optimizer(self, optimizer, optimizer_label, epoch_label):
        save_filename = 'opt_epoch_%s_id_%s.pth' % (epoch_label, optimizer_label)
        save_path = os.path.join(self._save_dir, save_filename)
        torch.save(optimizer.state_dict(), save_path)

    def _load_optimizer(self, optimizer, optimizer_label, epoch_label):
        load_filename = 'opt_epoch_%s_id_%s.pth' % (epoch_label, optimizer_label)
        load_path = os.path.join(self._save_dir, load_filename)
        assert os.path.exists(load_path), 'Weights file not found. %s ' \
                                          'Have you trained a model!? We are not providing one' % load_path

        optimizer.load_state_dict(torch.load(load_path))
        print('loaded optimizer: %s' % load_path)

    def _save_network(self, network, network_label, epoch_label):
        save_filename = 'net_epoch_%s_id_%s.pth' % (epoch_label, network_label)
        save_path = os.path.join(self._save_dir, save_filename)
        torch.save(network.state_dict(), save_path)
        print('saved net: %s' % save_path)

    def update_learning_rate(self):
        pass

    def print_network(self, network):
        num_params = 0
        for param in network.parameters():
            num_params += param.numel()
        print(network)
        print('Total number of parameters: %d' % num_params)

    def _get_scheduler(self, optimizer, opt):
        if opt.lr_policy == 'lambda':
            def lambda_rule(epoch):
                lr_l = 1.0 - max(0, epoch + 1 + opt.epoch_count - opt.niter) / float(opt.niter_decay + 1)
                return lr_l
            scheduler = lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda_rule)
        elif opt.lr_policy == 'step':
            scheduler = lr_scheduler.StepLR(optimizer, step_size=opt.lr_decay_iters, gamma=0.1)
        elif opt.lr_policy == 'plateau':
            scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.2, threshold=0.01, patience=5)
        else:
            return NotImplementedError('learning rate policy [%s] is not implemented', opt.lr_policy)
        return scheduler


class BaseRunnerModel(BaseModel):

    def __init__(self, opt):
        super(BaseRunnerModel, self).__init__(opt)

        self._name = 'BaseRunnerModel'

    def visualize(self, *args, **kwargs):
        raise NotImplementedError

    def inference(self, *args, **kwargs):
        raise NotImplementedError
