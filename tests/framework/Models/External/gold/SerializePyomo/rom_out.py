
# MODEL GENERATED BY RAVEN (raven.inl.gov)
import pyomo.environ as pyo
from pyomo.contrib.pynumero.interfaces.external_grey_box import ExternalGreyBoxModel, ExternalGreyBoxBlock
from pyomo.contrib.pynumero.dependencies import (numpy as np)
from pyomo.contrib.pynumero.asl import AmplInterface
from pyomo.contrib.pynumero.algorithms.solvers.cyipopt_solver import CyIpoptSolver, CyIpoptNLP
import os, sys, pickle
# RAVEN ROM PYOMO GREY MODEL CLASS

class ravenROM(ExternalGreyBoxModel):

  def __init__(self, **kwargs):
    self._rom_file = kwargs.get("rom_file")
    self._raven_framework = kwargs.get("raven_framework")
    self._raven_framework = os.path.abspath(self._raven_framework)
    if not os.path.exists(self._raven_framework):
      raise IOError('The RAVEN framework directory does not exist in location "' + str(self._raven_framework)+'" !')
    if os.path.dirname(self._raven_framework).endswith("framework"):
      sys.path.append(self._raven_framework)
    else:
      sys.path.append(os.path.join(self._raven_framework,"framework"))
    from CustomDrivers import DriverUtils as dutils
    dutils.doSetup()
    # de-serialize the ROM
    self._rom_file = os.path.abspath(self._rom_file)
    if not os.path.exists(self._rom_file):
      raise IOError('The serialized (binary) file has not been found in location "' + str(self._rom_file)+'" !')
    self.rom = pickle.load(open(self._rom_file, mode='rb'))
    #
    self.settings = self.rom.getInitParams()
    # get input names
    self._input_names = self.settings.get('Features')
    # n_inputs
    self._n_inputs = len(self._input_names)
    # get output names
    self._output_names = self.settings.get('Target')
    # n_outputs
    self._n_outputs = len(self._output_names)
    # input values storage
    self._input_values = np.zeros(self._n_inputs, dtype=np.float64)

  def return_train_values(self, feat):
    return self.rom.trainingSet.get(feat)

  def input_names(self):
    return self._input_names

  def output_names(self):
    return self._output_names

  def set_input_values(self, input_values):
    assert len(input_values) == self._n_inputs
    np.copyto(self._input_values, input_values)

  def evaluate_equality_constraints(self):
      raise NotImplementedError('This method should not be called for this model.')

  def evaluate_outputs(self):
    request = {k:np.asarray(v) for k,v in zip(self._input_names,self._input_values)}
    outs = self.rom.evaluate(request)
    eval_outputs = np.asarray([outs[k].flatten() for k in self._output_names], dtype=np.float64)
    return eval_outputs.flatten()

  def evaluate_jacobian_outputs(self):
    request = {k:np.asarray(v) for k,v in zip(self._input_names,self._input_values)}
    derivatives = self.rom.derivatives(request)
    jac = np.zeros((self._n_outputs, self._n_inputs))
    for tc, target in enumerate(self._output_names):
      for fc, feature in enumerate(self._input_names):
        jac[tc,fc] = derivatives['d{}|d{}'.format(target, feature)]
    return jac

def pyomoModel(ex_model):
  m = pyo.ConcreteModel()
  m.egb = ExternalGreyBoxBlock()
  m.egb.set_external_model(ex_model)
  for inp in ex_model.input_names():
    m.egb.inputs[inp].value = np.mean(ex_model.return_train_values(inp))
    m.egb.inputs[inp].setlb(np.min(ex_model.return_train_values(inp)))
    m.egb.inputs[inp].setub(np.max(ex_model.return_train_values(inp)))
  for out in ex_model.output_names():
    m.egb.outputs[out].value = np.mean(ex_model.return_train_values(out))
    m.egb.outputs[out].setlb(np.min(ex_model.return_train_values(out)))
    m.egb.outputs[out].setub(np.max(ex_model.return_train_values(out)))
  m.obj = pyo.Objective(expr=m.egb.outputs[out])

  return m

if __name__ == '__main__':
  for cnt, item in enumerate(sys.argv):
    if item.lower() == "-r":
      rom_file = sys.argv[cnt+1]
    if item.lower() == "-f":
      raven_framework = sys.argv[cnt+1]
  ext_model = ravenROM(**{'rom_file':rom_file,'raven_framework':raven_framework})
  concreteModel = pyomoModel(ext_model)
  ### here you should implement the optimization problem
  ###
  solver = pyo.SolverFactory('cyipopt')
  solver.config.options['hessian_approximation'] = 'limited-memory'
  results = solver.solve(concreteModel)
  print(results)
  count = 0
  with open("GrayModelOutput.txt", "r") as f:
    lines = f.readlines()
  with open("GrayModelOutput.txt", "w") as f:
    for line in lines:
        if line == "Problem:":
          count += 1
        if count == 1:
          f.write(line)
