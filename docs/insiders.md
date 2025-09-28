# Insiders

Hi, I'm Frank Hoffmann. I created and maintain inline-snapshot and several [other tools](https://github.com/15r10nk).
Working on open-source projects is incredibly rewarding, but it also requires a significant investment of time and energy. Balancing work, family, and open-source is challenging, and your support can make a real difference.

## Why sponsor?
By sponsoring me, you become an essential part of the future of inline-snapshot and related tools. Your support empowers me to spend more time building new features, improving usability, fixing bugs, and providing better documentation and support for everyone.

Open-source software powers the world, but most projects rely on volunteer work. Sponsoring helps create a more sustainable ecosystem, where maintainers can focus on quality and innovation instead of struggling to find time.

## What do you get when you sponsor me?

I want to create insider features that improve the usability of inline-snapshot.
These are first released for insiders only, which means you can access them when you sponsor me on GitHub.
They will later be released for everyone once a specific sponsoring goal is reached.

You will be able to run tests created with the insider version of inline-snapshot using the normal version. This is very important to me because it allows you to collaborate with others (in open-source or in your company) who do not use the insider version.
You can also use the normal inline-snapshot version to run your tests in CI.

The following features are currently available for sponsors:

### The ability to create and fix assertions without snapshot()

<video controls>
<source src="../assets/create_fix.mp4" type="video/mp4">
</video>

You can [create and fix normal assertions](fix_assert.md), which can be very useful when you work in a large codebase and want to use the inline-snapshot magic with your existing assertions, or when you want to create assertions but don't want to add inline-snapshot as a test dependency to your project.

### IDE integration into PyCharm

You are able to create snapshots by clicking the green "run test" button.
This is the first step toward extended [IDE integration](pycharm.md), and the ability to approve snapshot changes will follow in the future.

<video controls>
<source src="../assets/pycharm_run.mp4" type="video/mp4">
</video>

### For Companies

You can sponsor me as a company and email me a list of GitHub accounts that you want to be able to access the insider features.
It is still $10 per account, but you have only one sponsorship to manage.
I will also add your logo to my project readme when you sponsor me for more than $100 (see funding [tiers](https://github.com/sponsors/15r10nk)).

## Funding goals

One of my goals is to motivate people to start sponsoring open-source projects, not just mine.
Therefore, my plan is to reduce the minimum sponsoring amount, starting from $10 a month.

* *10 Sponsors:* [inline-snapshot-pandas](https://github.com/15r10nk/inline-snapshot-pandas) and [canonical-imports](https://github.com/15r10nk/canonical-imports) will be released.
* *20 Sponsors:* reduce the sponsorship amount to **$9**
* *40 Sponsors:* reduce the sponsorship amount to **$8**
* ... more goals will follow

I follow several goals with this plan:

1. I would like to convince many people and companies to sponsor open-source projects.
2. Lowering the minimum amount allows you to support other projects as well.
3. The ultimate goal is to have the time to work on my projects without having to offer sponsor-only features. I don't know if that will work out, but I think it's worth a try.

## Getting started

The inline-snapshot insider version is API-compatible with the normal inline-snapshot version, but offers several usability improvements.
Note that in order to access the Insiders repository, you need to become an eligible sponsor of [@15r10nk](https://github.com/sponsors/15r10nk) on GitHub with $10 per month or more.
You will then be invited to join the insider team and gain access to the repositories that are only accessible to insiders.

You can then install the insiders version with pip from the git repository:

``` bash
pip install git+ssh://git@github.com/15r10nk-insiders/inline-snapshot.git
```

This version offers you the features described at the top.
You can continue to use the inline-snapshot version you have downloaded after you stop sponsoring me, but you will no longer have access to the insider repository or updates.

## Every contribution counts!
Whether you’re an individual developer or a company, your sponsorship helps keep inline-snapshot moving forward. Together, we can make open-source better for everyone.
