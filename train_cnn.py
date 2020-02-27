import torch.optim as optim
import argparse
from models.baseline_cnn import BaselineCNN
import torch
import torch.nn as nn
from sklearn.model_selection import GridSearchCV
from skorch import NeuralNetClassifier
from data_pipeline.imagenet_pretrained import PretrainedImagenet
import copy
from torch.optim import lr_scheduler

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

def save_model(model, path):
    curr_dir = os.path.dirname(os.path.realpath(__file__))
    full_model_path = os.path.join(curr_dir, path)
    torch.save(model, full_model_path)

def train_neural_net(model, model_filepath, trainloader, evalloader, criterion, optimiser, scheduler, epochs=100, learning_rate=0.001):
    # GPU Stuff
    model.to(device)
    best_accuracy = 0
    best_model = copy.deepcopy(model.state_dict())
    for epoch in range(epochs):  # loop over the dataset multiple times
        running_loss = 0.0
        model.train()
        for i, data in enumerate(trainloader):
            inputs, labels = data[0].to(device), data[1].to(device)
            optimiser.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimiser.step()
            running_loss += loss.item()
            scheduler.step()
            if i % 100 == 0:
                print('[%d, %5d] loss: %.3f' %
                    (epoch + 1, i + 1, running_loss / 100))
                running_loss = 0.0
        # evaluate after each epoch
        print('Evaluation model')
        model.eval()
        loss, acc = evaluate_model_accuracy(model, evalloader, criterion)
        print('Evaluation loss', loss, 'evaluation accuracy', acc)
        if acc > best_accuracy:
            print('New best accuracy')
            best_model = copy.deepcopy(model.state_dict())
            best_accuracy = acc
    torch.save(best_model, model_filepath)

def evaluate_model_accuracy(model, evalloader, criterion):
    acc = 0
    loss = 0
    for x, y in evalloader:
        x = x.to(device)
        y = y.to(device)
        outputs = model(x)
        import ipdb; ipdb.set_trace()
        # what is the output shape
        _, preds = torch.max(outputs, 1)
        acc += (outputs == preds).sum()
        loss += criterion(outputs, y)
    N = len(evalloader.dataset)
    acc /= N
    loss /= N
    return loss, acc

def run_transfer_learning(trainloader, evalloader, last_layer_size):
    neural_net = PretrainedImagenet.get_resnet_feature_extractor_for_transfer(last_layer_size)
    criterion = nn.CrossEntropyLoss()
    optimiser = optim.SGD(neural_net.fc.parameters(), lr=0.001, momentum=0.9)
    scheduler = lr_scheduler.StepLR(optimiser, step_size=7, gamma=0.1)
    train_neural_net(neural_net, 'data_pipeline/saved_models/transferred_extractor', trainloader, evalloader, criterion, optimiser, scheduler)

def find_hyperparameters(training_images, training_labels):
    net = NeuralNetClassifier(
        BaselineCNN,
        max_epochs=10,
        lr=[0.1, 0.005],
        # Shuffle training data on each epoch
        iterator_train__shuffle=True,
    )
    params = {
        'lr': [0.01, 0.02],
        'max_epochs': [10, 20],
        'module__maxpool_kernel_size': [2, 4, 8],
        'module__out1': [6, 12, 18],
        'module__kernel1': [2, 4, 8],
        'module__in2': [2, 6, 12],
        'module_out2': [8, 16, 24],
        'module__kernel2': [2, 4, 8]
    }
    gs = GridSearchCV(net, params, refit=False, cv=3, scoring='accuracy')
    # TODO: X and y sizes are said not to match
    gs.fit(training_images, training_labels)
    print(gs.best_score_)
    return gs.best_params_
