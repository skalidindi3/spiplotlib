# -*- coding: utf-8 -*-

from collections import deque


# Helpers

def transpose(ll):
  return map(list, zip(*ll))

def bitList(b):
  return [int(bool((1<<(7-i)) & int(b))) for i in range(8)]

def bitTransitions(b, init_high=True):
  bl = bitList(b)
  dbl = [b for bb in [2*[i] for i in bl] for b in bb] # double & flatten
  bitstream = deque([int(init_high)] + dbl + [int(init_high)])
  transitions = []
  while len(bitstream) > 1:
    transitions.append((bitstream[0], bitstream[1]))
    bitstream.popleft()
  return transitions

def splitUnicodeString(s):
  return map(lambda c: c.encode("utf-8"), list(s.decode("utf-8")))


# Main Classes

class SpiPlot(object):
  boxChars = set(["━", "┃", "┏", "┓", "┗", "┛"])

  def __init__(self, show_bits=True, show_bytes=False,
               clk_color=2, mosi_color=3, miso_color=3,
               prefix_cycles=2, delay_cycles=2,
               clk_pullup=False, data_pullup=True,
               cs_active_low=True):
    self.show_bits = show_bits
    self.show_bytes = show_bytes
    self.clk_color = clk_color
    self.mosi_color = mosi_color
    self.miso_color = miso_color
    self.prefix_cycles = prefix_cycles
    self.delay_cycles = delay_cycles
    self.clk_pullup = clk_pullup
    self.data_pullup = data_pullup
    self.cs_active_low = cs_active_low

  @staticmethod
  def transitionToWaveform(key):
    return {
        (0,0): [" ", " ", "━"],
        (0,1): ["┏", "┃", "┛"],
        (1,1): ["━", " ", "-"],
        (1,0): ["┓", "┃", "┗"],
    }[key]

  # unicode is hard to split without decoding explicitly first
  @staticmethod
  def edgePairToBit(key):
    return {
        ("┓", " "): "0",
        ("┓", "━"): "1",
    }.get(key, " ")

  # modifies |waveform| in place
  @staticmethod
  def colorizeWaveform(waveform, color):
    if type(waveform[0]) == str:
      split_first = True
      waveform = map(splitUnicodeString, waveform)
    for i in range(len(waveform)):
      for j in range(len(waveform[i])):
        if waveform[i][j] in SpiPlot.boxChars:
          waveform[i][j] = "\033[38;5;%dm%s\033[0m" % (color, waveform[i][j])
    if split_first:
      waveform = map("".join, waveform)
    return waveform

  @staticmethod
  def combineWaveforms(waveform_list):
    return map("".join, transpose(waveform_list))

  @staticmethod
  def printWaveform(waveform, extra=1):
    for l in waveform:
      print "".join(l)
    for _ in range(extra):
      print

  def _getClkWaveform(self):
    bt = (8 * [(0,1), (1,0)]) + ((1 + self.delay_cycles*2) * [(0,0)])
    waveform = [self.transitionToWaveform(t) for t in bt]
    #self.colorizeWaveform(waveform, self.clk_color)
    transposed = transpose(waveform)
    return map("".join, transposed)

  def _getByteWaveform(self, b):#, color):
    bt = bitTransitions(b, self.data_pullup)
    if self.data_pullup:
      bt.extend([(1,1)] * self.delay_cycles*2)
    else:
      bt.extend([(0,0)] * self.delay_cycles*2)
    waveform = [self.transitionToWaveform(t) for t in bt]
    #self.colorizeWaveform(waveform, color)
    transposed = transpose(waveform)
    return map("".join, transposed)

  def _getDelayWaveform(self, pullup):#, color):
    if pullup:
      bt = 2 * self.prefix_cycles * [(1,1)]
    else:
      bt = 2 * self.prefix_cycles * [(0,0)]
    waveform = [self.transitionToWaveform(t) for t in bt]
    #self.colorizeWaveform(waveform, color)
    transposed = transpose(waveform)
    return map("".join, transposed)

  def getSpiClk(self, numbytes):
    clkws = [self._getDelayWaveform(self.clk_pullup)]#, self.clk_color)]
    clkws += numbytes * [self._getClkWaveform()]
    clkw = self.combineWaveforms(clkws)
    clkw = self.combineWaveforms([["     ", "SCLK ", "     "], clkw])
    return clkw

  def getSpiData(self, data, is_mosi):
    color = self.mosi_color if is_mosi else self.miso_color
    name = "MOSI " if is_mosi else "MISO "
    dataws = [self._getDelayWaveform(self.data_pullup)]#, color)]
    #dataws += map(lambda b: self._getByteWaveform(b, color), data)
    dataws += map(self._getByteWaveform, data)
    dataw = self.combineWaveforms(dataws)
    dataw = self.combineWaveforms([["     ", name, "     "], dataw])
    return dataw

  @staticmethod
  def analyzeWaveform(clkw, dataw):
    clkw0 = splitUnicodeString(clkw[0])
    dataw0 = splitUnicodeString(dataw[0])
    edge_pairs = zip(clkw0, dataw0)
    analyzed_bits = "".join(map(SpiPlot.edgePairToBit, edge_pairs))
    return analyzed_bits

  def _getByteAnnotations(self, bs):
    prefix = " " * (len("SCLK ") + self.prefix_cycles*2)
    annotations = map(lambda b: "            0x%02X" % b, bs)
    medians = " " * (self.delay_cycles*2 + 1)
    return prefix + medians.join(annotations)

  def printSpi(self, mosi, miso, show_bits=True, show_bytes=True):
    assert len(mosi) == len(miso), "MOSI & MISO lengths don't match"
    clkw = self.getSpiClk(len(mosi))
    mosiw = self.getSpiData(mosi, is_mosi=True)
    misow = self.getSpiData(miso, is_mosi=False)
    if self.show_bits:
      mosi_bits = self.analyzeWaveform(clkw, mosiw)
      miso_bits = self.analyzeWaveform(clkw, misow)
      mosiw.append(mosi_bits)
      misow.append(miso_bits)
    if self.show_bytes:
      mosiw.append(self._getByteAnnotations(mosi))
      misow.append(self._getByteAnnotations(miso))
    self.printWaveform(SpiPlot.colorizeWaveform(clkw, self.clk_color))
    self.printWaveform(SpiPlot.colorizeWaveform(mosiw, self.mosi_color))
    self.printWaveform(SpiPlot.colorizeWaveform(misow, self.miso_color))

