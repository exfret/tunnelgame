https://exfret.itch.io/tunnel/devlog/972099/so-im-getting-rid-of-variables

For a while now, I've been struggling with how to accurately capture story state during runtime. For example, if you picked up the acorn by the stream in the hills, I previously would done something like the following:

if: not hills_stream_acorn_picked_up
then:
  flag: hills_stream_acorn_picked_up
  set: acorns += 1

So the above code would check if the flag "hills_stream_acorn_picked_up" had been raised, then raise it and give you the acorn if not. The flag command doesn't just raise a flag however. Normally, you have to declare all variables in my program at the top so that I can check for spelling mistakes, type mismatches, etc. during parse time. Since any flag is just going to be a boolean, I don't force them to be declared at the top and instead auto-sense the names of all flags based off what appears next to a flag command. Thus, assuming we've declared the variable acorn earlier and also brushing aside some syntactical details, the above code is valid. However, the following would not work at all:

if: not hills_stream_acorn_picked_up
then:
  flag: picked_up_acorn_from_hills_stream
  set: acorns += 1

This is because hills_stream_acorn_picked_up would raise a MissingReference exception, indicating that the parser could not find it declared anywhere. This is _good_, since it means I can catch myself when I misspell things. Then, I can simply fix the spelling error, which is in the same area of the code (wherever this hills stream is), rather than at the very top where a globble's worth of other variables are being declared. In fact, despite the long names, _flags were easier to work with than full-fledged variables_. And I found myself using them everywhere! The reason was simple: the variable's declaration was close to where it was relevant.

So why not do that for regular variables? Well, in a story, basically everything has to be global in some way. A large swath of variables, for example, keep track of your inventory, and there's really no good place to put those variables other than at the root/global scope. It's not like I know ahead of time every single thing in the story where I want to give the player a coin! I know this sounds like just bad programming practice, but in my opinion, it's just a way of life with story-based games, or at least this specific one (a same truth holds for gotos). The fact that having these global flags wasn't actually so painful backs this up. But there was still something very wrong with the flag approach, and I just couldn't put my finger on it.

Around this time, I was also trying to add an object-world system, where you could easily write, maybe, a dialogue option for George whenever he's around without it depending on the location you're in. As long as George was in the same place (or in my own technical terminology, the same "block"), you could have these dialog options. And hey, maybe George has some state too, like he owns a number of coins? So, I started writing something like this:

world:
  George:
    choices:
      - choice: talk "Talk to George"
        outcome: (Insert conversation here)
    traits:
      - Has brown hair
      - Has some number of coins
    initial_location: Foyer
story:
  Orphanage:
    Foyer:
      - print: This is where you start!

Above, "world" is some special indicator that what follows is just background information, whereas "story" was for the actual executable story instructions, themselves split into blocks/sub-blocks. Though this was getting clunky. What was I going to do with the "traits"? They were just text so it's not like I could have checked his number of coins or anything fancy. And each new property like "initial_location" would have to have extra coding to support whatever I even decided it should be for. So I abandoned it.

Well, recently I was working on documentation for my story, and the way everything fit together when I wasn't tied to just locations was really neat. I was using a note-taking application called Obsidian that allows you to create links between your notes. When I wanted to brainstorm something related to George, I went to the George note I had. Then, I could write, for example, that he had 5 coins in that note. And the word "coin" would be a link to the note about coins. And if a place had something to do with George, I just wrote in that respective note what it had to do with him, with a link now to George on that page. Of course, not having to implement anything made it a lot easier, but something about just how much easier it was to do things when everything was in the right spot, made me realize that I shouldn't be organizing my story around variables in the first place. When I say as a storywriter that "George has 5 coins", I don't want to mean "george_coin_amount == 5". No, I want to write in some place relevant to George something relevant to coins. Well, I could do something like this:

George:
  vars:
    - coins: 5

The "vars" here would be a special block for variables related to George. I already have a construct like this for my stories, so that wouldn't be too hard to implement. But something is still wrong there: there's a variable and the name of this blog post implies I'm getting rid of them! Okay, more seriously though, other than the fact that the variable happens to be named "coins", there's nothing to relate it to that currency. To demonstrate the issue, I've been implementing an encyclopedia where you can look up terms. If I display somewhere that George has 5 coins, it would be nice to include a link to learn more about coins in the encyclopedia. But the only thing I have to go off of is what I happened to name the variable. I need to say George has 5 coins, not that the value of coin in George is 5. So I ended up going with something like this:

George:
  init:
    - instantiate: Coin
    - set: Coin.amount = 10
Coin(item):
  desc: This is where I'd put the encyclopedia page about coins.

Okay what the heck is going on there? Well, I essentially did a complete paradigm shift from procedural to object-oriented. Blocks are no longer just blocks of code to be executed, but can themselves have instances in other blocks. For example, Coins inherit from a built-in "item" type, which gives them an amount property by default. Then, when George is first created, he gets a Coin (the block), which includes in it a property with the number he has. (We don't want to actually instantiate 10 Coin blocks for performance reasons, but we could have done that, too). Finally, the amount property of the Coin instance inside George is set to 10.

Importantly, there are no more "vars" blocks. You can't just make a variable and set it to 10 globally. I might include some way to do this in the future, or maybe keep flags around at least, but for now I'm abandoning variables. Maybe this sounds extreme, but in writing my story and my documentation, I realized the following:

> Stories don't have bare numbers. Everything is an element of the story.

That is, you never want to give the character 5. You might want to give them 5 _coins_, or 5 _health_, but not just "5". And if you're giving them 5 coins, it's not too much to ask the author to somewhere just include a block about coins. For example, something like this:

Dungeon:
  - You find 5 {Coin}!
  - set: DaringHero:Coin.amount += 5
Coin(item):
  desc: A coin.
DaringHero:
  init:
    - instantiate: Coin

See how there's just a very simple block for "Coin" to indicate to the game that it's a thing? We're even able to "reference" it from within the text using a special {blop} syntax, so that I can make sure to highlight it as a keyword. I will say that sometimes thinking of everything as, well, a _thing_ in the story can be a little hard with programmer-brain. For example, health is so tempting to just make some global variable. But then it's impossible to reference where it's used from within the story, add encyclopedia pages on it, etc. After writing a bit with this approach, it's so much better.

There's a catch. I haven't actually coded any of this yet! (Notice how the title doesn't say "I got rid of variables"?) But I had dreams of blocks that message each other, move around, and parsing based on yaml, and I was able to turn those all into reality in the past year, so I believe that I can do this as well. And, I'm very excited to see how it turns out. For once, something doesn't feel "wrong" when I write my story. It feels natural, like how someone's thoughts would actually be organized. Huzzah to object oriented programming!