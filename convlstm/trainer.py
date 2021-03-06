import numpy as np
import cv2
import dataset
import torch
import torch.nn as nn
from torch.optim import Adam
import os
from tqdm import tqdm
from earlystopping import EarlyStopping
import matplotlib.pyplot as plt
import utils
import torch.nn.functional as F
import torch.optim as optim


def train(input_train, target_train, input_val, target_val, args, device):
    # model 결과 log dir
    log_dir = "./saver"
    log_heads = ['epoch', 'val_loss']
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    with open(os.path.join(log_dir, "log.csv"), 'w') as f:
        f.write(','.join(log_heads)+ '\n')

    # Seq2Seq -> nn.Sequential 클래스를 이용해 Multi Layer 구성을 만듬.
    endtoendmodel = model.Ensemble(convLSTM_parameters_list , num_layers=3, transpose_channels_list=transpose_channels_list).to(device)

    early_stopping = EarlyStopping(patience=5, improved_valid=True)


    if os.path.exists(os.path.join(args.save_dir, 'checkpoint.pth.tar')):
        # load existing model
        print('==> loading existing model')
        model_info = torch.load(os.path.join(args.save_dir, 'checkpoint.pth.tar'))
        endtoendmodel.load_state_dict(model_info['state_dict'])
        optimizer = torch.optim.Adam(model.parameters())
        optimizer.load_state_dict(model_info['optimizer'])
        cur_epoch = model_info['epoch'] + 1
    else:
        if not os.path.isdir(args.save_dir):
            os.makedirs(args.save_dir)
        cur_epoch = 0


    optimizer = Adam(endtoendmodel.parameters(), lr=args.initial_lr)

    scheduler = optim.lr_scheduler.LambdaLR(optimizer=optimizer,
                                            lr_lambda=lambda epoch: 0.95 ** epoch,
                                            last_epoch=-1,
                                            verbose=False)

    loss_function = nn.CrossEntropyLoss()


    for epoch in range(cur_epoch, args.max_epoch+1):
        train_loss = 0
        for batch_num, (input, target) in enumerate(zip(input_train, target_train)):
            optimizer.zero_grad()
            endtoendmodel.train()
            input, target = input.to(device), target.to(device)
            output = endtoendmodel(input)
            loss = torch.sqrt(loss_function(output, target))
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        train_loss /= len(input_train.dataset)
        scheduler.step()

        val_loss = 0
        endtoendmodel.eval()
        with torch.no_grad():
            for input, target in zip(input_val, target_val):
                input, target = input.to(device), target.to(device)
                output = endtoendmodel(input)
                loss = torch.sqrt(loss_function(output, target))
                val_loss += loss

        val_loss /= len(input_val.dataset)

        print(f"Epoch: {epoch} Training Loss: {train_loss}, Validation Loss: {val_loss}")

        model_dict = {
            'epoch': epoch,
            'state_dict': endtoendmodel.state_dict(),
            'optimizer': optimizer.state_dict()
        }

        early_stopping(val_loss.item(), model_dict, epoch, args.save_dir, log_dir)
        if early_stopping.early_stop:
            print("Early stopping")
            break