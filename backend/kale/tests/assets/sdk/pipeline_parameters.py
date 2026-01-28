# Copyright 2025 The Kubeflow Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from kale.sdk import pipeline, step


@step(name="step1")
def step1():
    return 10


@step(name="step2")
def step2(var1, var2, data):
    print(var1 + var2)
    return "Test"


@step(name="step3")
def step3(st, st2):
    print(st)


@pipeline(
    name="test",
    experiment="test",
    )
def mypipeline(a=1, b="Some string", c=5):
    data = step1()
    res = step2(c, a, data)
    step3(b, data)


if __name__ == "__main__":
    mypipeline(c=4, b="Test")
