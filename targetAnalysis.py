import cv2 as cv
import numpy as np
from matplotlib import pyplot as plt
import math
from aenum import Enum
import sys


class MarkStatus(Enum):
    otimo = 4
    bom = 3
    medio = 2
    ruim = 1
    ausente = 0

class Board:

    def __init__(self, image):
        self.TPs = []
        self.img = image

    def identifyCircles(self):

        imgDrawn = cv.cvtColor(self.img, cv.COLOR_GRAY2BGR)

        # tratamento para limitar qnts circulos devem ser  identificados na imagem

        brightness = 265
        contrast = 300
        imgTemp = self.img * (contrast/127+1) - contrast + brightness
        imgTemp = np.uint8(imgTemp)
        imgTemp = cv.medianBlur(imgTemp, 7)
        circles = cv.HoughCircles(
            imgTemp, cv.HOUGH_GRADIENT, 1, 50, param1=220, param2=32, minRadius=25, maxRadius=40)

        # old paramenters!!
        # circles = cv.HoughCircles(imgTemp, cv.HOUGH_GRADIENT, 1, 50,
        # param1=200, param2=30, minRadius=25, maxRadius=40)

        print(len(circles[0])-1)

        circles_first = circles
        circles = np.uint16(np.around(circles))
        for i in circles[0, :]:
            cv.circle(imgDrawn, (i[0], i[1]), i[2], (0, 255, 0), 2)
            cv.circle(imgDrawn, (i[0], i[1]), 2, (0, 0, 255), 3)

        showimg(imgDrawn)

        return imgDrawn, circles, circles_first

    def formatImage(self, valorX, valorY, raio, aX, aY, TPcount=0):
        
        imgCut = self.img[valorY - raio:valorY+raio, valorX-raio:valorX+raio]
        a = np.double(imgCut)
        b = a - 97
        imgCut = np.uint8(b)

        # ret, imgBinaryCut = cv.threshold(
        #     imgCut, 0, 255, cv.THRESH_BINARY+cv.THRESH_OTSU)

        imgBinaryCut = cv.adaptiveThreshold(
            imgCut, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY, 27, 15)

        if(imgBinaryCut is not None):
            location = [aX, aY]
            TPName = "PT00" + str(TPcount)
            self.TPs.append(
                TestPoint(TPName, imgBinaryCut, location))

        return imgBinaryCut

    def __str__(self):

        escreveTPs = []
        for TP in self.TPs:
            escreveTPs.append(str(TP))
        return("Lista de PTs: " + str(escreveTPs))


class TestPoint:

    def __init__(self, name, image, location):
        self.name = name
        self.image = image
        self.location = location
        self.probeMarkCenterList = []
        self.probeMarkMin = ()
        self.probeMarkMax = ()
        self.identMarkCenter()
        self.status = None
        self.markStatus()
        

    def identMark(self, pix):
        # tipos inválidos:
        # - marcação única
        # - marcação em traço
        pontos = []

        y = 0
        for linha in self.image:
            #print(linha)
            x = 0
            for pix in linha:
                # encontrou um ponto
                if pix == 0:
                    pontos.append([x,y])
                x += 1
            y += 1
        marcas = []
            
        for ponto in pontos:
            if marcas == []:
                marcas.append([ponto])
                pontos.remove(ponto)
            else:
                existe = False
                for marca in marcas:
                    for p in marca:
                        distanciaEntreDoisPontos = math.sqrt(((p[0] - ponto[0])**2) + ((p[1] - ponto[1])**2))
                        #print(distanciaEntreDoisPontos)
                        if(distanciaEntreDoisPontos <= 2):
                            marca.append(ponto)
                            #pontos.remove(ponto)
                            existe = True
                            break
                if existe == False:
                        marcas.append([ponto])
                            
        #print(marcas)

##        for marca in marcas:
##            print("Marca: ", marca)
        
        return marcas

    def identMarkCenter(self):

        tolerancia = raio * 0.15

        pixLargura = ((self.location[0]+raio) -
                      (self.location[0]-raio))/len(self.image)
        pixAltura = ((self.location[1]+raio) -
                     (self.location[1]-raio))/len(self.image[0])

        marcas = self.identMark(int(pixLargura))

        arrayMarkX = []
        arrayMarkY = []
        
        for marca in marcas:
            tempX = []
            tempY = []
            for ponto in marca:
                tempX.append(ponto[0])
                tempY.append(ponto[1])
            arrayMarkX.append(tempX)
            arrayMarkY.append(tempY)
            
        for marcaX, marcaY in zip(arrayMarkX, arrayMarkY):
            larguraMarcacao = (pixLargura*max(marcaX)) - pixLargura*min(marcaX)
            alturaMarcacao = (pixAltura*max(marcaY)) - pixAltura*min(marcaY)
            centroMarkX = min(marcaX) + larguraMarcacao/2
            centroMarkY = min(marcaY) + alturaMarcacao/2
            markLocation = [centroMarkX, centroMarkY]

            if((math.sqrt(((centroMarkX - (len(self.image)/2))**2) + ((centroMarkY - (len(self.image[0])/2))**2))) < (raio - tolerancia)):
                self.probeMarkCenterList.append(markLocation)
                self.probeMarkMin = (min(marcaX) - 1, min(marcaY) - 1)
                self.probeMarkMax = (max(marcaX) + 1, max(marcaY) + 1)

    def markStatus(self):
        if len(self.probeMarkCenterList) == 0:
            self.status = MarkStatus.ausente
            return

        checkH = 0
        percent = 0
        present = False
        for i in self.probeMarkCenterList:
            aX = i[0] - raio
            aY = i[1] - raio
            h = (aX**2+aY**2)**0.5
            checkH = h
            percentC = checkH*100/raio
            if(percentC <= 100):
                if percent < percentC:
                    percent = percentC
                    present = True

        if present == False:
            self.status = MarkStatus.ausente
        else:
            if (percent < 20.0):
                self.status = MarkStatus.otimo
            elif ((percent > 20.0) and (percent < 60)):
                self.status = MarkStatus.bom
            # elif ((percent > 50.0) and (percent < 75.0)):
            #     self.status = MarkStatus.medio
            elif (percent >= 60.0):
                self.status = MarkStatus.ruim

        return

    def __str__(self):

        return("Nome: " + self.name + " - Localização na placa: " +
               str(self.location) + " - Status: " + str(self.status) +
               " - Localização das marcaççoes: " + str(self.probeMarkCenterList))


def drawBadCircle(img, xLocPt, yLocPt, B, G, R, nome):
    cv.circle(img, (xLocPt, yLocPt), 60, (B, G, R), 9)
    cv.putText(img, nome, (xLocPt - 100, yLocPt - 100),
               0, 2, (255, 255, 255), 4)
    return


def showimg(img1, img2=None, img3=None):
    plt.style.use('grayscale')  # cor de fundo do plt
    plt.imshow(img1)
    plt.title('original'), plt.xticks([]), plt.yticks([])

    plt.colorbar()
    plt.show()
    cv.destroyAllWindows()


if __name__ == "__main__":

    img0 = cv.imread('img/imgTest.jpg', cv.IMREAD_GRAYSCALE)
    img1 = cv.cvtColor(img0, cv.COLOR_GRAY2BGR)

    board = Board(img0)

    valor = 1
    imgDrawn, Circle, CircleFirst = board.identifyCircles()
    for i, a in zip(Circle[0, :], CircleFirst[0, :]):

        aX = a[0]
        aY = a[1]
        valorX = i[0]
        valorY = i[1]
        raio = i[2]

        imgBinaryCut = board.formatImage(
                valorX, valorY, raio, aX, aY, valor)

        if(imgBinaryCut is not None):
            print(board.TPs[-1])
            imgMarcada = cv.cvtColor(imgBinaryCut, cv.COLOR_GRAY2BGR)
            if board.TPs[-1].probeMarkMin is not ():
                cv.rectangle(imgMarcada, board.TPs[-1].probeMarkMin, board.TPs[-1].probeMarkMax,(0,255,0),1)
                showimg(imgMarcada)
        valor += 1

    for Pts in board.TPs:
        
        yLocPt = Pts.location[1]
        xLocPt = Pts.location[0]
        xLocPt = xLocPt.astype('int32')
        yLocPt = yLocPt.astype('int32')

        if len(Pts.probeMarkCenterList) > 1:
             drawBadCircle(img1, xLocPt, yLocPt, 255, 255, 0, Pts.name)
        else:
            if Pts.probeMarkCenterList == MarkStatus.ruim:
                drawBadCircle(img1, xLocPt, yLocPt, 0, 0, 255, Pts.name)
            elif Pts.status == MarkStatus.ausente:
                drawBadCircle(img1, xLocPt, yLocPt, 255, 255, 255, Pts.name)
            elif Pts.status == MarkStatus.bom:
                drawBadCircle(img1, xLocPt, yLocPt, 0, 255, 180, Pts.name)
            elif Pts.status == MarkStatus.otimo:
                drawBadCircle(img1, xLocPt, yLocPt, 0, 255, 0, Pts.name)

    # showimg(img1)
    cv.imwrite("img/newImg.jpg", img1)
    # print(board)
