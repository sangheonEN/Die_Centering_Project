import datetime
import os.path as osp
import numpy as np
import pytz
import utils
import os
from importlib import import_module


class solver_inf(object):
    def __init__(self, test_data_loader, opts):
        self.test_data_loader = test_data_loader
        self.num_class = len(self.test_data_loader.dataset.class_names)


        if opts.model == "deeplabv3":
            model_module = import_module('models.{}.deeplabv3_{}'.format(
                opts.backbone, opts.backbone_layer))
            self.model = model_module.Deeplabv3(n_class=self.num_class)
        else:
            model_module = import_module('models.{}.fcn_{}'.format(
                opts.backbone, opts.backbone_layer))
            self.model = model_module.FCN(n_class=self.num_class)

        self.model.resume(opts.resume, test=opts.mode in ['inference'])
        self.model.to(opts.cuda)

class Inference_f(solver_inf):
    def __init__(self, test_data_loader, opts):
        super(Inference_f, self).__init__(test_data_loader, opts)
        self.cuda = opts.cuda
        self.opts = opts
        self.test_data_loader = test_data_loader

        if opts.mode in ['inference']:
            return

    def Test(self):
        count = 0
        label_trues = list()
        label_preds = list()
        timestamp_start = datetime.datetime.now(pytz.timezone('Asia/Seoul'))

        log_headers = [
            'LIST_NUM',
            'TEST/acc',
            'TEST/acc_cls',
            'TEST/mean_iu',
            'TEST/fwavacc',
            'elapsed_time',
        ]
        
        if not osp.exists(osp.join(os.path.dirname(os.path.abspath(__file__)), 'inference_result')):
            os.makedirs(osp.join(os.path.dirname(os.path.abspath(__file__)), 'inference_result'))
            with open(osp.join(osp.join(os.path.dirname(os.path.abspath(__file__)), 'inference_result'), 'log_inference_result.csv'), 'w') as f:
                f.write(','.join(log_headers) + '\n')
                

        for image, label in self.test_data_loader:
            lbl_pred = utils.run_fromfile(self.model,
                                    image,
                                    self.opts.cuda)


            lbl_pred = lbl_pred.data.max(1)[1].cpu().numpy()[:, :, :]
            

            for img, lt, lp in zip(image, label, lbl_pred):
                # ?????? torch?????? convolution operation??? ?????? transform(data shape, normalization)??? ??? ????????????
                # untransform??? ?????? ?????? shape??? normalization ???????????????. ???????????? ????????? ????????? ???????????? ??????
                img, lt = self.test_data_loader.dataset.untransform(img, lt)
                lp = np.expand_dims(lp, -1)
                
                # visualization
                utils.decode_segmap_save(lp.squeeze(), self.num_class, flag_pred=True, cnt=count)
                utils.decode_segmap_save(lt, self.num_class, flag_pred=False, cnt=count)
                
                label_trues.append(lt)
                label_preds.append(lp)
                count+=1

        metrics = utils.label_accuracy_score(label_trues, label_preds, n_class=self.num_class)

        with open(osp.join(os.path.dirname(os.path.abspath(__file__)), 'inference_result', 'log_inference_result.csv'), 'a') as f:
            elapsed_time = (
                    datetime.datetime.now(pytz.timezone('America/Bogota')) -
                    timestamp_start).total_seconds()
            log = [count] + list(metrics) + [elapsed_time]
            log = map(str, log)
            f.write(','.join(log) + '\n')