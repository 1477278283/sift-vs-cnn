import pandas as pd
import argparse
from data_pipeline.dataloaders import get_pretrained_imagenet_dataloader
from data_pipeline.utils import read_images, get_all_data_from_loader
from sklearn.svm import SVC
from sklearn.model_selection import cross_val_score
from utils import get_indices_and_labels

def get_argparser():
    parser = argparse.ArgumentParser(description='Obtain SIFT features for training set')
    parser.add_argument("-root", "--image-root", type=str, default="data/images_small",
                        help="The path to the image data folder")
    parser.add_argument("-train-idx", "--training-index-file", type=str, default="data/Butterfly200_train_release.txt",
                        help="The path to the file with training indices")
    parser.add_argument("-test-idx", "--test-index-file", type=str, default="data/Butterfly200_test_release.txt",
                        help="The path to the file with test indices")
    parser.add_argument("-s", "--species-file", type=str, default="data/species.txt",
                        help="The path to the file with mappings from index to species name")
    parser.add_argument("-sift-size", "--sift-feature-size", type=int, help="The feature size for SIFT")
    parser.add_argument("-sift-path", "--sift-feature-path", type=str, help="The path to SIFT features")
    parser.add_argument("-N", "--no-images", required=True, type=int, help="The amount of images to use in building features")
    parser.add_argument("-l", "--label-index", required=True, type=int, help="Which index to use as the label, between 1 and 5. Use 1 o classify species, 5 to classify families.")
    parser.add_argument("-ex", "--imagenet-extractor-path", required=True, type=str, help="Path to model pretrained with Imagenet and trained with transfer learning")
    parser.add_argument("-imagenet", "--imagenet-features", required=True, type=str, help="Path to imagenet features")
    parser.add_argument("-kernel", "--svm-kernel", default="linear", help="SVM kernel to use in classification")
    # TODO: add reduced dims
    return parser

if __name__ == "__main__":
    parser = get_argparser()
    args = parser.parse_args()
    N = args.no_images
    batch_size = N
    label_i = args.label_index
    training_indices, training_labels = get_indices_and_labels(args.training_index_file, args.label_index)
    training_images = read_images(args.image_root, training_indices, N, grey=False)
    test_indices, test_labels = get_indices_and_labels(args.test_index_file, args.label_index)
    test_images = read_images(args.image_root, test_indices, 1000, grey=False)
    imagenet_feature_dataloader = get_pretrained_imagenet_dataloader(training_images, training_labels[:N], training_labels.nunique(), \
                                                                        batch_size, args.imagenet_features, args.imagenet_extractor_path)
    imagenet_features, imagenet_labels = get_all_data_from_loader(imagenet_feature_dataloader)
    test_imagenet_feature_dataloader = get_pretrained_imagenet_dataloader(test_images, test_labels[:1000], test_labels.nunique(), \
                                                                        batch_size, args.imagenet_features + '_test', args.imagenet_extractor_path)
    imagenet_features, imagenet_labels = get_all_data_from_loader(imagenet_feature_dataloader)
    test_imagenet_features, test_imagenet_labels = get_all_data_from_loader(test_imagenet_feature_dataloader)
    print('Got features')
    classifier = SVC(kernel=args.svm_kernel)
    classifier.fit(imagenet_features, imagenet_labels)
    imagenet_scores = classifier.score(test_imagenet_features, test_imagenet_labels)
    print('Imagenet scores', imagenet_scores)
