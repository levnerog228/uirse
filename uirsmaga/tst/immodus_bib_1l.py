import numpy as np

def RGBtoHSL(r,g,b):
    R = r / 255
    G = g / 255
    B = b / 255
    Ma = 0
    if (R >= G) and (R >= B):
        Kmax = 1
        Ma = R
    if (G >= R) and (G >= B):
        Kmax = 2
        Ma = G
    if (B >= R) and (B >= G):
        Kmax = 3
        Ma = B
    Mi = 0
    if (R <= G) and (R <= B):
        Kmin = 1
        Mi = R
    if (G <= R) and (G <= B):
        Kmin = 2
        Mi = G
    if (B <= R) and (B <= G):
        Kmin = 3
        Mi = B
    L = (Ma + Mi) / 2
    Lp = round((L*100), 0)
    Sk = 1
    H = 0
    if (Ma == Mi):
        Sk = 0
        S = 0
    if (Sk > 0) and (L <= 0.5):
        S = (Ma - Mi) / (Ma + Mi)
    if (Sk > 0) and (L > 0.5):
        S = (Ma - Mi) / (2 - Ma - Mi)
    Sp = round((S * 100), 0)
    if (Kmax == 1) and (Ma != Mi):
        H = (G - B)/(Ma - Mi)
        H = H * 60
        if (H < 0):
            H = H + 360
    if (Kmax == 2) and (Ma != Mi):
        H = 2 + (B - R) / (Ma - Mi)
        H = H * 60
        if (H < 0):
            H = H + 360
    if (Kmax == 3) and (Ma != Mi):
        H = 4 + (R - G) / (Ma - Mi)
        H = H * 60
        if (H < 0):
            H = H + 360
    H = int(round(H, 0))
    Mas = np.zeros((1, 3,), float)
    Mas[0][0] = H
    Mas[0][2] = Lp
    Mas[0][1] = Sp
    return Mas

def HSLtoRGB(H,Sp,Lp):
    S = Sp / 100
    L = Lp / 100
    if (S == 0):
        R = L * 255
        G = R
        B = R
    if (S > 0):
        if (L < 0.5):
            temp1 = L * (1 + S)
        if (L >= 0.5):
            temp1 = L + S - L * S
        temp2 = 2 * L - temp1
        H = H / 360
        tempR = H + 0.333
        tempG = H
        tempB = H - 0.333
        if (tempR < 0):
            tempR = tempR + 1
        if (tempR > 1):
            tempR = tempR - 1
        if (tempG < 0):
            tempG = tempG + 1
        if (tempG > 1):
            tempG = tempG - 1
        if (tempB < 0):
            tempB = tempB + 1
        if (tempB > 1):
            tempB = tempB - 1
        if (6 * tempR < 1):
            R = temp2 + (temp1 - temp2) * 6 * tempR
        if (6 * tempR >= 1):
            if (2 * tempR < 1):
                R = temp1
            if (2 * tempR >= 1):
                if (3 * tempR < 2):
                    R = temp2 + (temp1 - temp2) * (0.666 - tempR) * 6
                if (3 * tempR >= 2):
                    R = temp2
        if (6 * tempG < 1):
            G = temp2 + (temp1 - temp2) * 6 * tempG
        if (6 * tempG >= 1):
            if (2 * tempG < 1):
                G = temp1
            if (2 * tempG >= 1):
                if (3 * tempG < 2):
                    G = temp2 + (temp1 - temp2) * (0.666 - tempG) * 6
                if (3 * tempG >= 2):
                    G = temp2
        if (6 * tempB < 1):
            B = temp2 + (temp1 - temp2) * 6 * tempB
        if (6 * tempB >= 1):
            if (2 * tempB < 1):
                B = temp1
            if (2 * tempB >= 1):
                if (3 * tempB < 2):
                    B = temp2 + (temp1 - temp2) * (0.666 - tempB) * 6
                if (3 * tempB >= 2):
                    B = temp2
    r = int(round((R * 255), 0))
    g = int(round((G * 255), 0))
    b = int(round((B * 255), 0))
    MasO = np.zeros((1, 3,), float)
    MasO[0][0] = r
    MasO[0][1] = g
    MasO[0][2] = b
    return MasO

def ArrayToFile (fname1,fname2,fname3,M1,M2,M3):
    c1 = np.savetxt(fname1, M1, delimiter=', ')
    c2 = np.savetxt(fname2, M2, delimiter=', ')
    c3 = np.savetxt(fname3, M3, delimiter=', ')

def HSLFindH(zvetH,S,L,JarkFon,NasishFon,zvetFon,zvetVibor,zvetNew,Delta):
    if (zvetH < zvetVibor-Delta) or (zvetH > zvetVibor+Delta):
       L = JarkFon
       S = NasishFon
       zvetH = zvetFon
    if (zvetH >= zvetVibor-Delta) and (zvetH <= zvetVibor+Delta):
       zvetH = zvetNew
    return zvetH, S, L

def RGBNew(picture,MasR,MasG,MasB):
    width, height = picture.size
    for x in range(width):
       for y in range(height):
          k1 = int(MasR[y][x])
          k2 = int(MasG[y][x])
          k3 = int(MasB[y][x])
          cur_col = picture.getpixel((x, y))
          picture.putpixel((x, y), (cur_col[0] * 0 + k1, cur_col[1] * 0 + k2, cur_col[2] * 0 + k3))
    return picture