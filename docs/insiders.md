# Insiders

Hi, I'm Frank Hoffmann I created and maintain inline-snapshot and several [other tools](https://github.com/15r10nk).
Working on open-source projects is really exciting but requires also a lot of time.
Being able to finance my work allows me to put more time into my projects.

Many open-source projects follow a *sponsorware* strategy where they build new features for insiders first and release them when they have reached a specific funding goal.
This is not an option for most of the inline-snapshot features, because this would force everyone who wants to run the tests of a project to become a sponsor when the maintainer want to use insider-only features of inline-snapshot which require some new API.

But there are some features which require no new API and provide you a lot of value.
Fixing raw assertions like the following is one of them:

=== "original code"
    <!-- inline-snapshot: first_block outcome-failed=1 -->
    ``` python
    def test_assert():
        assert 1 + 1 == 5
    ```

=== "--inline-snapshot=fix-assert"
    <!-- inline-snapshot: requires_assert outcome-passed=1 -->
    ``` python hl_lines="2"
    def test_assert():
        assert 1 + 1 == 2
    ```

And this is what I want to offer for my sponsors, the ability to [create and fix normal assertions](fix_assert.md).

But I also want to make use of funding-goals, where I want to reduce the minimum amount, starting from 10$ a month. The last sponsoring goal will make fixing of raw assertions available for everyone.

I follow some goals with this plan:

1. I would like to convince many people/companies to sponsor open source projects.
2. Lowering the minimum amount allows you to support other projects as well.
3. The ultimate goal is to have the time and money to work on my projects without having to offer sponsor-only features. I don't know if that will work out, but I think it's worth a try.

I don't currently have a detailed plan for when I will reduce the funding amount for the first time or which functions I will make available to everyone, because I don't know how things will develop.
The future will be exciting.

## Getting started

The inline-snapshot insider version is API-compatible with the normal inline-snapshot version, but allows to [fix assertions](fix_assert.md).
Note that in order to access the Insiders repository, you need to become an eligible sponsor of [@15r10nk](https://github.com/sponsors/15r10nk) on GitHub with 10$ per month or more.
You will then be invited to join the insider team and gain access to the repositories that are only accessible to insiders.


### Installation

You can install the insiders version with pip from the git repository:

``` bash
pip install git+ssh://git@github.com/15r10nk-insiders/inline-snapshot.git
```
