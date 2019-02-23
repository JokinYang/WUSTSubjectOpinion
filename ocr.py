import os, cv2
from PIL import Image

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.externals import joblib
import pickle
import requests
import time
import requests
from skimage import feature as ft


def hog(img):
	return ft.hog(img)


def hog_fromarray(arr):
	img = Image.fromarray(arr)
	f = ft.hog(img, block_norm='L2-Hys', pixels_per_cell=(2, 2), cells_per_block=(2, 2))
	return f


def del_blur(img):
	# 双边滤波 去噪 效果不错
	m_blur = cv2.bilateralFilter(img, 9, 75, 75)
	# oust 滤波 二值化图片
	ret, oust_img = cv2.threshold(m_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

	fin = cv2.bilateralFilter(oust_img, 9, 75, 75)
	return fin


def split_img(img):
	hs = 3
	h = 14
	w = 11
	ws1 = 3
	ws2 = 13
	ws3 = 23
	ws4 = 33
	img1 = img[hs:hs + h, ws1:ws1 + w]
	img2 = img[hs:hs + h, ws2:ws2 + w]
	img3 = img[hs:hs + h, ws3:ws3 + w]
	img4 = img[hs:hs + h, ws4:ws4 + w]
	return img1, img2, img3, img4


class ORC:
	def __init__(self):
		self.svm = SVC(kernel='rbf', random_state=0, gamma='auto', C=1.0, probability=True)
		self.sc = StandardScaler()
		self.score_ = None

	def fit(self, X, y, test_size=0.3, sample_weight=None):
		X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size,
															random_state=0)
		self.sc.fit(X_train)
		X_train_std = self.sc.transform(X_train)
		X_test_std = self.sc.transform(X_test)

		self.svm.fit(X_train_std, y_train, sample_weight=sample_weight)

		y_pred = self.svm.predict(X_test_std)
		self.score_ = accuracy_score(y_test, y_pred)

	def _transform(self, X):
		return self.sc.transform(X)

	def predict(self, X):
		return self.svm.predict(self._transform(X))

	def predict_proba(self, X):
		return self.svm.predict_proba(self._transform(X))

	def score(self):
		return self.score_


def load_ocr() -> ORC:
	return joblib.load('wust.orc')


_orc = load_ocr()


def predict(x: bytes):
	img = None
	if isinstance(x, bytes):
		with open('temp.png', 'wb') as f:
			f.write(x)
		img = cv2.imread('temp.png', 0)
		os.remove('temp.png')
	if isinstance(x, str) and os.path.isfile(x):
		img = cv2.imread(x, 0)

	img_arr = del_blur(img)
	l = []
	for x in split_img(img_arr):
		l.append(hog_fromarray(x))
	pred = _orc.predict(l)
	return ''.join(pred)


if __name__ == '__main__':
	url = 'http://jwxt.wust.edu.cn/whkjdx/verifycode.servlet?0.12337475696465894'
	con = requests.get(url).content
	print(predict(con))
