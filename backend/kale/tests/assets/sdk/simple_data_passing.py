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

from kale.sdk import step, pipeline


@step(name="step1", limits={"amd/gpu": "1"})
def step1():
    a = 1
    b = 2
    return a, b


@step(name="step2",
      retry_count=5,
      retry_interval="20",
      retry_factor=2,
      timeout=5)
def step2(a, b):
    c = a + b
    print(c)
    return c


@step(name="step3", annotations={"step3-annotation": "test"})
def step3(a, c):
    d = c + a
    print(d)


@pipeline(
    name="test",
    experiment="test",
    steps_defaults={"labels": {"common-label": "true"}}
)
def mypipeline():
    _b, _a = step1()
    _c = step2(_b, _a)
    step3(_a, _c)


if __name__ == "__main__":
    mypipeline()
