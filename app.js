/* $kitles — live lyric sync player */

/* ── Data ─────────────────────────────────────────────────────────────── */

const ALBUMS = [
  { id: 'sslp',  name: 'The Slim Shady LP',          year: 1999, color: '#f4c430', emoji: '😈' },
  { id: 'mmlp',  name: 'The Marshall Mathers LP',     year: 2000, color: '#8b0000', emoji: '🎭' },
  { id: 'tes',   name: 'The Eminem Show',              year: 2002, color: '#1a3a5c', emoji: '🎪' },
  { id: 'enc',   name: 'Encore',                       year: 2004, color: '#c0392b', emoji: '🎤' },
  { id: 'rel',   name: 'Relapse',                      year: 2009, color: '#1e4d2b', emoji: '💊' },
  { id: 'rec',   name: 'Recovery',                     year: 2010, color: '#4a235a', emoji: '⚡' },
  { id: 'mmlp2', name: 'The Marshall Mathers LP 2',   year: 2013, color: '#7d3c12', emoji: '🔥' },
  { id: 'rev',   name: 'Revival',                      year: 2017, color: '#154360', emoji: '🌊' },
  { id: 'kami',  name: 'Kamikaze',                     year: 2018, color: '#2c3e50', emoji: '💣' },
  { id: 'mtbmb', name: 'Music to Be Murdered By',     year: 2020, color: '#212121', emoji: '🔪' },
];

const SONGS = [
  {
    id: 1, title: 'My Name Is', album: 'sslp', duration: 264,
    lyrics: [
      { t:  2, l: 'Hi! My name is... (what?) My name is... (who?)' },
      { t:  7, l: 'My name is... Slim Shady' },
      { t: 11, l: 'Hi! My name is... (huh?) My name is... (what?)' },
      { t: 15, l: 'My name is... Slim Shady' },
      { t: 20, l: 'Excuse me! Can I have the attention of the class for one second?' },
      { t: 27, l: "Hi kids, do you like violence?" },
      { t: 31, l: "Wanna see me stick Nine Inch Nails through each one of my eyelids?" },
      { t: 36, l: "Wanna copy me and do exactly like I did?" },
      { t: 40, l: "Try 'cid and get f***ed up worse than my life is?" },
      { t: 45, l: 'My brain is dead weight, I\'m tryin\' to get my head straight' },
      { t: 49, l: "But I can't figure out which Spice Girl I want to impregnate" },
      { t: 53, l: "And Dr. Dre said, \"Slim Shady you a basehead\"" },
      { t: 57, l: "Uh-uh! \"So why's your face red? Man, you wasted!\"" },
      { t: 62, l: "Well since age twelve I've felt like I'm someone else" },
      { t: 66, l: "Cause I hung my original self from the top of a shelf" },
      { t: 70, l: 'Hi! My name is... (what?) My name is... (who?)' },
      { t: 74, l: 'My name is... Slim Shady' },
    ]
  },
  {
    id: 2, title: 'The Real Slim Shady', album: 'sslp', duration: 284,
    lyrics: [
      { t:  4, l: 'May I have your attention please?' },
      { t:  7, l: 'May I have your attention please?' },
      { t: 10, l: 'Will the real Slim Shady please stand up?' },
      { t: 13, l: "I repeat, will the real Slim Shady please stand up?" },
      { t: 17, l: "We're gonna have a problem here..." },
      { t: 22, l: "Y'all act like you never seen a white person before" },
      { t: 26, l: "Jaws all on the floor like Pam, like Tommy just burst in the door" },
      { t: 31, l: 'And started whoopin\' her ass worse than before' },
      { t: 35, l: 'They first were divorced, throwin\' her over furniture' },
      { t: 39, l: "It's the return of the... \"Ah, wait, no way, you're kidding" },
      { t: 44, l: 'He didn\'t just say what I think he did, did he?"' },
      { t: 48, l: "And Dr. Dre said... nothing, you idiots!" },
      { t: 52, l: "Dr. Dre's dead, he's locked in my basement! (Ha-ha!)" },
      { t: 57, l: "Feminist women love Eminem" },
      { t: 60, l: '"Chicka chicka chicka, Slim Shady, I\'m sick of him' },
      { t: 64, l: 'Look at him, walkin\' around grabbin\' his you-know-what' },
      { t: 68, l: 'Flippin\' the you-know-who," "Yeah, but he\'s so cute though!"' },
      { t: 73, l: 'Yeah, I probably got a couple of screws up in my head loose' },
      { t: 77, l: 'But no worse than what\'s goin\' on in your parents\' bedrooms' },
      { t: 81, l: 'Sometimes I wanna get on TV and just let loose' },
      { t: 85, l: "But can't, but it's cool for Tom Green to hump a dead moose" },
      { t: 90, l: '"My bum is on your lips, my bum is on your lips"' },
      { t: 94, l: 'And if I\'m lucky you might just give it a little kiss' },
      { t: 98, l: 'And that\'s the message that we deliver to little kids' },
      { t: 102, l: 'And expect them not to know what a woman\'s clitoris is' },
      { t: 106, l: 'Of course they gonna know what intercourse is' },
      { t: 110, l: 'By the time they hit fourth grade' },
      { t: 113, l: "They got the Discovery Channel, don't they?" },
      { t: 117, l: '"We ain\'t nothing but mammals," well, some of us cannibals' },
      { t: 121, l: "Who cut other people open like cantaloupes" },
      { t: 125, l: 'But if we can hump dead animals and antelopes' },
      { t: 129, l: 'Then there\'s no reason that a man and another man can\'t elope' },
      { t: 134, l: 'Will the real Slim Shady please stand up?' },
      { t: 137, l: 'Please stand up, please stand up?' },
      { t: 140, l: "'Cause I'm Slim Shady, yes I'm the real Shady" },
      { t: 143, l: 'All you other Slim Shadys are just imitating' },
      { t: 147, l: "So won't the real Slim Shady please stand up" },
      { t: 150, l: 'Please stand up, please stand up?' },
    ]
  },
  {
    id: 3, title: 'Stan', album: 'mmlp', duration: 403,
    lyrics: [
      { t:  0, l: '[Verse 1 — Stan]' },
      { t:  4, l: "My tea's gone cold, I'm wondering why I" },
      { t:  8, l: "Got out of bed at all" },
      { t: 12, l: "The morning rain clouds up my window" },
      { t: 16, l: "And I can't see at all" },
      { t: 20, l: "And even if I could it'd all be gray" },
      { t: 24, l: "But your picture on my wall" },
      { t: 28, l: "It reminds me that it's not so bad, it's not so bad" },
      { t: 36, l: "Dear Slim, I wrote you but you still ain't callin'" },
      { t: 40, l: "I left my cell, my pager and my home phone at the bottom" },
      { t: 44, l: "I sent two letters back in autumn, you must not have got 'em" },
      { t: 48, l: "There probably was a problem at the post office or somethin'" },
      { t: 52, l: "Sometimes I scribble addresses too sloppy when I jot 'em" },
      { t: 56, l: "But anyways, f*** it, what's been up, man? How's your daughter?" },
      { t: 60, l: "My girlfriend's pregnant too, I'm 'bout to be a father" },
      { t: 64, l: "If I have a daughter, guess what I'm a call her?" },
      { t: 67, l: "I'ma name her Bonnie" },
      { t: 70, l: "I read about your Uncle Ronnie too, I'm sorry" },
      { t: 74, l: "I had a friend kill himself over some b**** that didn't want him" },
      { t: 78, l: "I know you probably hear this every day" },
      { t: 82, l: "But I'm your biggest fan" },
      { t: 85, l: "I even got the underground s*** that you did with Skam" },
      { t: 89, l: "I got a room full of your posters and your pictures, man" },
      { t: 93, l: "I like the s*** you did with Rawkus too, that s*** was fat" },
      { t: 97, l: "Anyway, I hope you get this, man, hit me back" },
      { t: 101, l: "Just to chat, truly yours, your biggest fan, this is Stan" },
      { t: 108, l: '[Chorus]' },
      { t: 112, l: "My tea's gone cold, I'm wondering why I" },
      { t: 116, l: "Got out of bed at all..." },
    ]
  },
  {
    id: 4, title: 'The Way I Am', album: 'mmlp', duration: 291,
    lyrics: [
      { t:  3, l: "I sit back with this pack of Zig Zags and this bag" },
      { t:  7, l: "Of this weed it gives me the s*** needed to be" },
      { t: 11, l: "The most meanest MC on this — on this Earth" },
      { t: 15, l: "And since birth I've been cursed with this curse to just curse" },
      { t: 19, l: "And just blurt this berserk and bizarre s***" },
      { t: 23, l: "That works and it sells and it helps" },
      { t: 27, l: "In case you can't tell" },
      { t: 30, l: "To me, dealing with stress" },
      { t: 33, l: "I am not afraid to take a stand" },
      { t: 37, l: "'Cause I am whatever you say I am" },
      { t: 41, l: "If I wasn't, then why would I say I am?" },
      { t: 45, l: "In the paper, the news, everyday I am" },
      { t: 49, l: "Radio won't even play my jam" },
      { t: 53, l: "'Cause I am whatever you say I am" },
      { t: 57, l: "If I wasn't, then why would I say I am?" },
      { t: 61, l: "In the paper, the news, everyday I am" },
      { t: 65, l: "I don't know, it's just the way I am" },
    ]
  },
  {
    id: 5, title: 'Lose Yourself', album: 'tes', duration: 326,
    lyrics: [
      { t:  2, l: "Look, if you had one shot, or one opportunity" },
      { t:  6, l: "To seize everything you ever wanted" },
      { t:  9, l: "In one moment" },
      { t: 11, l: "Would you capture it, or just let it slip?" },
      { t: 15, l: "His palms are sweaty, knees weak, arms are heavy" },
      { t: 19, l: "There's vomit on his sweater already, mom's spaghetti" },
      { t: 23, l: "He's nervous, but on the surface he looks calm and ready" },
      { t: 27, l: "To drop bombs, but he keeps on forgettin'" },
      { t: 31, l: "What he wrote down, the whole crowd goes so loud" },
      { t: 35, l: "He opens his mouth, but the words won't come out" },
      { t: 39, l: "He's chokin', how, everybody's jokin' now" },
      { t: 43, l: "The clocks run out, times up, over — blaow!" },
      { t: 47, l: "Snap back to reality, ope there goes gravity" },
      { t: 51, l: "Ope, there goes Rabbit, he choked, he's so mad but he won't" },
      { t: 55, l: "Give up that easy, nope, he won't have it" },
      { t: 59, l: "He knows his whole back's to these ropes, it don't matter" },
      { t: 63, l: "He's dope, he knows that but he's broke, he's so stagnant" },
      { t: 67, l: "He knows when he goes back to his mobile home, that's when it's" },
      { t: 71, l: "Back to the lab again, yo, this whole rhapsody" },
      { t: 75, l: "He better go capture this moment and hope it don't pass him" },
      { t: 79, l: "You better lose yourself in the music, the moment" },
      { t: 83, l: "You own it, you better never let it go" },
      { t: 87, l: "You only get one shot, do not miss your chance to blow" },
      { t: 91, l: "This opportunity comes once in a lifetime yo" },
      { t: 95, l: "You better lose yourself in the music, the moment" },
      { t: 99, l: "You own it, you better never let it go" },
      { t: 103, l: "You only get one shot, do not miss your chance to blow" },
      { t: 107, l: "This opportunity comes once in a lifetime" },
      { t: 111, l: "The soul's escaping through this hole that is gaping" },
      { t: 115, l: "This world is mine for the taking, make me king" },
      { t: 119, l: "As we move toward a new world order" },
      { t: 123, l: "A normal life is boring, but superstardom's close to post-mortem" },
      { t: 127, l: "It only grows harder, homie grows hotter" },
      { t: 131, l: "He blows, it's all over, these hoes is all on him" },
      { t: 135, l: "Coast to coast shows, he's known as the globetrotter" },
      { t: 139, l: "Lonely roads, God only knows, he's grown farther from home" },
      { t: 143, l: "He goes home and barely knows his own daughter" },
      { t: 147, l: "But hold your nose 'cause here goes the cold water" },
      { t: 151, l: "His bosses don't want him no more, he's cold product" },
      { t: 155, l: "They moved on to the next schmoe who flows" },
      { t: 159, l: "He nose-dove and sold nada, so the soap opera" },
      { t: 163, l: "Is told and unfolds, I suppose it's old partner" },
      { t: 167, l: "But the beat goes on da-da dum da dum da da da da" },
      { t: 171, l: "You better lose yourself in the music, the moment" },
      { t: 175, l: "You own it, you better never let it go" },
      { t: 179, l: "You only get one shot, do not miss your chance to blow" },
      { t: 183, l: "This opportunity comes once in a lifetime yo" },
    ]
  },
  {
    id: 6, title: 'Without Me', album: 'tes', duration: 290,
    lyrics: [
      { t:  2, l: "Obie Trice, real name, no gimmicks" },
      { t:  6, l: "Two trailer park girls go 'round the outside" },
      { t: 10, l: "'Round the outside, 'round the outside" },
      { t: 14, l: "Two trailer park girls go 'round the outside" },
      { t: 18, l: "'Round the outside, 'round the outside" },
      { t: 22, l: "Guess who's back, back again" },
      { t: 25, l: "Shady's back, tell a friend" },
      { t: 28, l: "Guess who's back, guess who's back" },
      { t: 31, l: "Guess who's back, guess who's back" },
      { t: 34, l: "Guess who's back, guess who's back" },
      { t: 37, l: "Guess who's back... na-na-na-na-na-na-na-na-na" },
      { t: 42, l: "I've created a monster, 'cause nobody wants to" },
      { t: 46, l: "See Marshall no more, they want Shady, I'm chopped liver" },
      { t: 50, l: "Well if you want Shady, this is what I'll give ya" },
      { t: 54, l: "A little bit of weed mixed with some hard liquor" },
      { t: 58, l: "Some vodka that'll jump-start my heart quicker" },
      { t: 62, l: "Than a shock when I get shocked at the hospital" },
      { t: 66, l: "By the doctor when I'm not cooperating" },
      { t: 70, l: "When I'm rocking the table while he's operating" },
      { t: 74, l: "Hey! Do you want to hear me moan?" },
      { t: 78, l: "You waited this long, now stop debating" },
      { t: 82, l: "'Cause I'm back, I'm on the rag and ovulating" },
      { t: 86, l: "I know that you got a job, Ms. Cheney" },
      { t: 90, l: "But your husband's heart problem's complicated" },
      { t: 94, l: "So the FCC won't let me be" },
      { t: 97, l: "Or let me be me so let me see" },
      { t: 100, l: "They tried to shut me down on MTV" },
      { t: 103, l: "But it feels so empty without me" },
      { t: 107, l: "So come on and dip, bum on your lips" },
      { t: 111, l: "F*** that, come on and jump for this" },
      { t: 115, l: "Jump, jump, jump" },
      { t: 118, l: "So come on and dip, bum on your lips" },
    ]
  },
  {
    id: 7, title: 'Mockingbird', album: 'enc', duration: 290,
    lyrics: [
      { t:  3, l: "I know sometimes things may not always make sense to you right now" },
      { t:  8, l: "But hey, what daddy always tell you?" },
      { t: 12, l: "Straighten up little soldier" },
      { t: 15, l: "Stiffen up that upper lip" },
      { t: 18, l: "What you crying about? You got me" },
      { t: 22, l: "Hailie, I know you miss your mom and I know you miss your dad" },
      { t: 28, l: "When I'm gone but I'm trying to give you the life that I never had" },
      { t: 34, l: "I can see you're sad, even when you smile, even when you laugh" },
      { t: 40, l: "I can see it in your eyes, deep inside you want to cry" },
      { t: 46, l: "'Cause you're scared, I ain't there?" },
      { t: 49, l: "Daddy's with you in your prayers" },
      { t: 52, l: "No more crying, wipe them tears" },
      { t: 55, l: "Daddy's here, no more nightmares" },
      { t: 58, l: "We gonna pull together through it, we gonna do it" },
      { t: 61, l: "Laney, uncle's crazy, ain't he?" },
      { t: 64, l: "Yeah but he loves you girl and you better know it" },
      { t: 68, l: "We're all we got in this world" },
      { t: 71, l: "When it spins, when it swirls" },
      { t: 74, l: "When it whirls, when it twirls" },
      { t: 77, l: "Two little beautiful girls" },
      { t: 80, l: "Lookin' puzzled, in a daze" },
      { t: 83, l: "I know it's confusing you" },
      { t: 86, l: "Daddy's always on the move, mama's always on the news" },
      { t: 90, l: "I try to keep you sheltered from it but somehow it seems" },
      { t: 94, l: "The harder that I try to do that, the more it backfires on me" },
      { t: 98, l: "All the things growing up as daddy that he had to see" },
      { t: 102, l: "Daddy don't want you to see but you see just as much as he did" },
      { t: 106, l: "We did not plan it to be this way, your mom and me" },
      { t: 110, l: "But things have gotten so bad between us" },
      { t: 113, l: "I don't see us ever being able to live together ever again" },
      { t: 118, l: "Like we used to when you was a baby, maybe one day" },
      { t: 122, l: "Sweetie all I can say is..." },
      { t: 125, l: "Hush little baby, don't you cry" },
      { t: 129, l: "Everything's gonna be alright" },
      { t: 133, l: "Stiffen that upper lip up, little lady I told ya" },
      { t: 137, l: "Daddy's here to hold ya through the night" },
      { t: 141, l: "I know mommy's not here right now and we don't know why" },
      { t: 145, l: "We feel how we feel inside" },
      { t: 148, l: "It may seem a little crazy, pretty baby" },
      { t: 152, l: "But I promise mama's gon' be alright" },
    ]
  },
  {
    id: 8, title: 'Not Afraid', album: 'rec', duration: 258,
    lyrics: [
      { t:  2, l: "I'm not afraid (I'm not afraid)" },
      { t:  5, l: "To take a stand (to take a stand)" },
      { t:  8, l: "Everybody (everybody)" },
      { t: 11, l: "Come take my hand (come take my hand)" },
      { t: 14, l: "We'll walk this road together, through the storm" },
      { t: 18, l: "Whatever weather, cold or warm" },
      { t: 21, l: "Just letting you know that you're not alone" },
      { t: 25, l: "Holla if you feel like you've been down the same road (same road)" },
      { t: 30, l: "Yeah, it's been a ride" },
      { t: 33, l: "I guess I had to go to that place to get to this one" },
      { t: 37, l: "Now some of you might still be in that place" },
      { t: 41, l: "If you're trying to get out, just follow me" },
      { t: 44, l: "I'll get you there" },
      { t: 47, l: "You can try and read my lyrics off of this paper before I lay 'em" },
      { t: 51, l: "But you won't take the sting out these words before I say 'em" },
      { t: 55, l: "'Cause ain't no way I'ma let you stop me from causing mayhem" },
      { t: 59, l: "When I say 'em or do something I do it" },
      { t: 63, l: "I don't give a damn what you think" },
      { t: 66, l: "I'm doing this for me, so f*** the world" },
      { t: 70, l: "Feed it beans, it's gas-powered" },
      { t: 73, l: "Seems to be upset" },
      { t: 76, l: "When it sees me with my sleeves rolled up" },
      { t: 79, l: "Crease in my jeans, act like they seen a teen, idol scream" },
      { t: 83, l: "No, I'm not on drugs" },
      { t: 86, l: "I'm on a roll, call it rock and roll" },
      { t: 89, l: "But I need to be straight, so today I made a vow" },
      { t: 93, l: "That I'ma be emotionally available now" },
      { t: 97, l: "I'm not afraid to take a stand" },
      { t: 101, l: "Everybody, come take my hand" },
      { t: 105, l: "We'll walk this road together, through the storm" },
      { t: 109, l: "Whatever weather, cold or warm" },
    ]
  },
  {
    id: 9, title: 'Love the Way You Lie', album: 'rec', duration: 263,
    lyrics: [
      { t:  1, l: "Just gonna stand there and watch me burn" },
      { t:  5, l: "But that's alright because I like the way it hurts" },
      { t:  9, l: "Just gonna stand there and hear me cry" },
      { t: 13, l: "But that's alright because I love the way you lie" },
      { t: 17, l: "I love the way you lie" },
      { t: 20, l: "I love the way you lie" },
      { t: 25, l: "I can't tell you what it really is" },
      { t: 29, l: "I can only tell you what it feels like" },
      { t: 33, l: "And right now it's a steel knife in my windpipe" },
      { t: 37, l: "I can't breathe but I still fight while I can fight" },
      { t: 41, l: "As long as the wrong feels right it's like I'm in flight" },
      { t: 45, l: "High off of love, drunk from my hate" },
      { t: 49, l: "It's like I'm huffing paint and I love it the more that I suffer" },
      { t: 53, l: "I suffocate and right before I'm about to drown" },
      { t: 57, l: "She resuscitates me, she f***ing hates me" },
      { t: 61, l: "And I love it, 'wait, where you going?'" },
      { t: 65, l: "'I'm leaving you!', 'No you ain't come back'" },
      { t: 69, l: "We're running right back, here we go again" },
      { t: 73, l: "It's so insane 'cause when it's going good it's going great" },
      { t: 77, l: "I'm Superman with the wind at his back" },
      { t: 81, l: "She's Lois Lane but when it's bad it's awful" },
      { t: 85, l: "I feel so ashamed, I snap" },
      { t: 88, l: "'Who's that dude?' 'I don't even know his name'" },
      { t: 92, l: "I laid hands on her, I'll never stoop so low again" },
      { t: 96, l: "I guess I don't know my own strength" },
      { t: 100, l: "Just gonna stand there and watch me burn" },
      { t: 104, l: "But that's alright because I like the way it hurts" },
      { t: 108, l: "Just gonna stand there and hear me cry" },
      { t: 112, l: "But that's alright because I love the way you lie" },
    ]
  },
  {
    id: 10, title: "Won't Back Down", album: 'rec', duration: 268,
    lyrics: [
      { t:  3, l: "You can sound the alarm, you can call out your guards" },
      { t:  7, l: "You can fence in your yard, you can pull all the cards" },
      { t: 11, l: "But I won't back down" },
      { t: 14, l: "Oh no, I won't back down" },
      { t: 18, l: "You can stand me up at the gates of hell" },
      { t: 22, l: "But I won't back down" },
      { t: 25, l: "No, I'll stand my ground" },
      { t: 28, l: "Won't be turned around" },
      { t: 31, l: "And I'll keep this world from dragging me down" },
      { t: 35, l: "Gonna stand my ground and I won't back down" },
    ]
  },
  {
    id: 11, title: 'Rap God', album: 'mmlp2', duration: 363,
    lyrics: [
      { t:  2, l: "Look, I was gonna go easy on you and not to hurt your feelings" },
      { t:  6, l: "But I only got one opportunity coming your way" },
      { t: 10, l: "'Cause some dude dissed me, now I got to school him" },
      { t: 14, l: "Seize the moment and I don't want to miss the chance to blow" },
      { t: 18, l: "This opportunity comes once in a lifetime" },
      { t: 22, l: "Yo" },
      { t: 24, l: "I'm beginning to feel like a Rap God, Rap God" },
      { t: 28, l: "All my people from the front to the back nod, back nod" },
      { t: 32, l: "Now who thinks their arms are long enough to slap box, slap box?" },
      { t: 36, l: "They said I rap like a robot, so call me Rapbot" },
      { t: 40, l: "But for me to rap like a computer must be in my genes" },
      { t: 44, l: "I got a laptop in my back pocket" },
      { t: 47, l: "My pen'll go off when I half-cock it" },
      { t: 50, l: "Got a fat knot from that rap profit" },
      { t: 53, l: "Made a living and a killing off it" },
      { t: 56, l: "Ever since Bill Clinton was still in office" },
      { t: 59, l: "With Monica Lewinsky feeling on his nut-sack" },
      { t: 63, l: "I'm an MC still as honest" },
      { t: 66, l: "But as honest as the day is long, the double M is back" },
      { t: 70, l: "Now this looks like a job for me so everybody just follow me" },
      { t: 74, l: "'Cause we need a little controversy" },
      { t: 77, l: "'Cause it feels so empty without me" },
      { t: 80, l: "I'm not trying to ruin your holy matrimony" },
      { t: 84, l: "I'm just trying to get the message out to homies" },
      { t: 88, l: "Supersonically" },
      { t: 91, l: "I'm beginning to feel like a Rap God, Rap God" },
      { t: 95, l: "All my people from the front to the back nod, back nod" },
      { t: 99, l: "Now who thinks their arms are long enough to slap box, slap box?" },
      { t: 103, l: "Let me show you maintaining this s*** ain't that hard" },
      { t: 107, l: "Everybody wants the key and the secret to rap immortality like I have got" },
      { t: 113, l: "Well, to be truthful the blueprint's simply rage and youthful exuberance" },
      { t: 118, l: "Everybody loves to root for a nuisance" },
      { t: 122, l: "Hit the earth like an asteroid, did nothing but shoot for the moon since" },
      { t: 126, l: "Pun intended, word to Mel Gibson" },
      { t: 129, l: "He's no longer sugar coating s***" },
      { t: 132, l: "Now I'm about to crack skulls and make a fuss" },
      { t: 136, l: "Imma give you all my verses, every one of 'em is worth it" },
      { t: 140, l: "All the s*** that I been holding back forever, perfect" },
      { t: 144, l: "Uh, sama lamaa duma lamaa you assuming I'm a human" },
      { t: 148, l: "What I gotta do to get it through to you I'm superhuman" },
      { t: 152, l: "Innovative and I'm made of rubber so that anything you say is" },
      { t: 156, l: "Ricocheting off of me and it'll glue to you and I'm devastating" },
      { t: 160, l: "More than ever demonstrating" },
      { t: 163, l: "How to give a motherf***ing audience a feeling like it's levitating" },
      { t: 167, l: "Never fading and I know that haters are forever waiting" },
      { t: 171, l: "For the day that they can say I fell off, they'd be celebrating" },
      { t: 175, l: "'Cause I know the way to get 'em motivated" },
      { t: 178, l: "I make elevating music, you make elevator music" },
      { t: 182, l: "Oh, he's too mainstream" },
      { t: 185, l: "Well, that's what they do when they get jealous, they confuse it" },
      { t: 189, l: "'Shut up b****, I'm going to be rapping for the next decade" },
      { t: 193, l: "And if you don't like it, you can'" },
      { t: 196, l: "I'm beginning to feel like a Rap God, Rap God" },
    ]
  },
  {
    id: 12, title: 'Legacy', album: 'mmlp2', duration: 275,
    lyrics: [
      { t:  3, l: "As a child I stayed to myself" },
      { t:  7, l: "I was antisocial" },
      { t: 10, l: "I'm not gonna lie to you" },
      { t: 13, l: "I was a loner" },
      { t: 16, l: "Didn't feel the need to talk to people" },
      { t: 20, l: "Just felt like I was somewhat of an introverted kid" },
      { t: 25, l: "So when hip-hop came to me" },
      { t: 28, l: "It was like a best friend" },
      { t: 31, l: "I didn't need a friend anymore, I had hip-hop" },
      { t: 36, l: "I used to be the type of kid that would always think" },
      { t: 40, l: "The sky is falling" },
      { t: 42, l: "Now I think the fact that I'm differently wired's awesome" },
      { t: 46, l: "'Cause if I wasn't, I wouldn't be able to work" },
      { t: 50, l: "Words the way I do and connect at this level" },
      { t: 54, l: "Mad Hatter as a child singing" },
      { t: 58, l: "All the answers that you seek" },
      { t: 61, l: "Can never be found" },
      { t: 64, l: "But I finally figured out" },
      { t: 67, l: "That maybe one day I'll leave a legacy" },
    ]
  },
  {
    id: 13, title: 'Guts Over Fear', album: 'mmlp2', duration: 291,
    lyrics: [
      { t:  4, l: "I've been running from something, I've been living in fear" },
      { t:  8, l: "I've been trying to find something within myself to steer" },
      { t: 12, l: "Past the darkness in my mind" },
      { t: 15, l: "And maybe just maybe I need to leave it all behind" },
      { t: 20, l: "How many times will I be able to pull me out of this spin?" },
      { t: 25, l: "Every time I'm saved by something or someone I begin" },
      { t: 29, l: "Feeling like maybe I'm destined to do this" },
      { t: 33, l: "I don't know it though, but I think this is it, this is it" },
      { t: 38, l: "I write it down and it feels like I'm revealing a truth" },
      { t: 42, l: "From a place deep inside me that I never knew" },
      { t: 46, l: "Look at all of the ones that I've hurt" },
      { t: 49, l: "Couldn't get past 'em like they were a wall" },
      { t: 53, l: "God, I'm surprised I haven't quit" },
      { t: 56, l: "My heart could take this much more" },
      { t: 59, l: "It takes guts to do this" },
      { t: 62, l: "Guts over fear" },
    ]
  },
  {
    id: 14, title: 'Walk on Water', album: 'rev', duration: 304,
    lyrics: [
      { t:  3, l: "I walk on water" },
      { t:  6, l: "But only when it freezes" },
      { t:  9, l: "'Cause I'm only human" },
      { t: 12, l: "Just like you" },
      { t: 15, l: "Making my mistakes" },
      { t: 18, l: "Oh if you only knew" },
      { t: 21, l: "I don't think you should believe the hype" },
      { t: 25, l: "Or even believe my rhymes" },
      { t: 29, l: "You shouldn't think I walk on water" },
      { t: 33, l: "Only Jesus can" },
      { t: 36, l: "I have a tendency to" },
      { t: 39, l: "Put too much pressure on me" },
      { t: 43, l: "Sometimes I trip and fall" },
      { t: 46, l: "And feel like I'm sinking in" },
      { t: 49, l: "The sea" },
      { t: 52, l: "I'm only human, just like you" },
      { t: 56, l: "Making my mistakes" },
      { t: 60, l: "Oh if you only knew" },
      { t: 64, l: "I don't think you should believe the hype" },
      { t: 68, l: "Or even believe my rhymes" },
    ]
  },
  {
    id: 15, title: 'Fall', album: 'kami', duration: 318,
    lyrics: [
      { t:  2, l: "Somebody said I need to let bygones be bygones" },
      { t:  6, l: "I'll cry all I want when it's time for me to be gone" },
      { t: 10, l: "'Cause what they see in me is what I fight to be, oh Lord" },
      { t: 14, l: "And I can see it right and wrong I'm fighting to be right" },
      { t: 18, l: "Tryna see the light, tryna see the light" },
      { t: 22, l: "But this darkness won't let up" },
      { t: 25, l: "I feel the monster inside me growing stronger" },
      { t: 28, l: "No wonder I can't sleep" },
      { t: 31, l: "Okay, thought I had it figured out" },
      { t: 35, l: "But I'm second-guessing, maybe I did it wrong" },
      { t: 39, l: "Maybe this is all a bad dream" },
      { t: 42, l: "And I'll wake up and be a pop star again" },
      { t: 46, l: "But the fall's gonna happen" },
      { t: 49, l: "Either by my hand or someone else's" },
      { t: 53, l: "So I'm calling you out" },
    ]
  },
  {
    id: 16, title: 'Lucky You', album: 'kami', duration: 199,
    lyrics: [
      { t:  1, l: "I be the thing that you need" },
      { t:  4, l: "Shoot first, ask questions last" },
      { t:  7, l: "That's how most legends are made" },
      { t: 10, l: "I don't care what you think" },
      { t: 13, l: "As long as it's about me" },
      { t: 16, l: "The best thing since wrestling" },
      { t: 19, l: "Lyrical miracle spiritual" },
      { t: 23, l: "Highly sexual, controversial" },
      { t: 27, l: "Something about you I like" },
      { t: 30, l: "Cause you're different than the rest" },
      { t: 33, l: "You passed the test, you showed me love" },
      { t: 37, l: "Now I gotta give you what you've been dreaming of" },
      { t: 41, l: "So lucky you" },
      { t: 44, l: "Lucky you, lucky, lucky you" },
      { t: 48, l: "Now I got a right to talk" },
      { t: 51, l: "'Cause I worked for it" },
      { t: 54, l: "Through the hurt of it" },
      { t: 57, l: "Every person that I push out of the way" },
      { t: 61, l: "I had to murder them" },
    ]
  },
  {
    id: 17, title: 'Darkness', album: 'mtbmb', duration: 363,
    lyrics: [
      { t:  3, l: "Here I am alone again" },
      { t:  7, l: "Can't get out of this hole I'm in" },
      { t: 11, l: "It's like the walls are caving in" },
      { t: 15, l: "You can't escape, you can't escape" },
      { t: 19, l: "Pour me another drink" },
      { t: 22, l: "I don't wanna feel a thing" },
      { t: 25, l: "What does it matter anymore" },
      { t: 28, l: "Darkness, darkness, darkness all around" },
      { t: 32, l: "Darkness, darkness everywhere" },
      { t: 36, l: "I got nowhere to run" },
      { t: 39, l: "And I got nowhere to hide" },
      { t: 43, l: "But it's darkness" },
      { t: 46, l: "Here I am alone again" },
      { t: 50, l: "Can't get out of this hole I'm in" },
      { t: 54, l: "It's like the walls are caving in" },
      { t: 58, l: "You can't escape, you can't escape" },
    ]
  },
  {
    id: 18, title: 'Those Kinda Nights', album: 'mtbmb', duration: 212,
    lyrics: [
      { t:  2, l: "Those kinda nights" },
      { t:  5, l: "Where you're up all night thinking about your life" },
      { t:  9, l: "And you realize that everything you thought was right" },
      { t: 13, l: "Was a lie" },
      { t: 16, l: "Those kinda nights" },
      { t: 19, l: "Where you're asking God, why?" },
      { t: 22, l: "Why am I?" },
      { t: 24, l: "Here on this earth?" },
      { t: 27, l: "What's my purpose?" },
      { t: 30, l: "I just wanna feel like I'm worth it" },
      { t: 33, l: "Those kinda nights" },
      { t: 36, l: "Those kinda nights" },
    ]
  },
];

/* ── State ─────────────────────────────────────────────────────────────── */

const state = {
  currentSong: null,
  playing: false,
  elapsed: 0,
  shuffle: false,
  repeat: false,
  volume: 80,
  currentView: 'home',
  currentAlbum: null,
  lyricsPanelOpen: false,
  activeLyricIdx: -1,
  ticker: null,
};

/* ── Helpers ───────────────────────────────────────────────────────────── */

const $ = id => document.getElementById(id);
const albumById = id => ALBUMS.find(a => a.id === id);
const fmt = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

function albumArtStyle(album) {
  return `background: linear-gradient(135deg, ${album.color}cc, ${album.color}44);`;
}

function buildSongRow(song, idx, showAlbum = false, matchSnippet = null) {
  const album = albumById(song.album);
  const row = document.createElement('div');
  row.className = 'song-row' + (state.currentSong?.id === song.id ? ' playing' : '');
  row.dataset.songId = song.id;

  row.innerHTML = `
    <div class="song-row-num">
      <span class="num-text">${idx}</span>
      <svg class="play-icon" viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
    </div>
    <div class="song-row-info">
      <div class="song-row-title">${song.title}</div>
      <div class="song-row-album">${showAlbum ? album.name + ' · ' : ''}${album.year}</div>
      ${matchSnippet ? `<div class="song-row-match">${matchSnippet}</div>` : ''}
    </div>
    <div></div>
    <div class="song-row-duration">${fmt(song.duration)}</div>
  `;

  row.addEventListener('click', () => playSong(song));
  return row;
}

/* ── Views ─────────────────────────────────────────────────────────────── */

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
  $(`view-${name}`)?.classList.remove('hidden');
  document.querySelectorAll('.nav-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.view === name);
  });
  state.currentView = name;
}

function renderHome() {
  const hour = new Date().getHours();
  $('greeting-time').textContent = hour < 12 ? 'Morning' : hour < 18 ? 'Afternoon' : 'Evening';
  $('home-count').textContent = SONGS.length;
  $('live-counter-text').textContent = `${SONGS.length} tracks · ${SONGS.reduce((s, x) => s + x.lyrics.length, 0)} lyric lines indexed`;

  const fc = $('featured-albums');
  fc.innerHTML = '';
  ALBUMS.forEach(album => {
    const songs = SONGS.filter(s => s.album === album.id);
    if (!songs.length) return;
    const card = document.createElement('div');
    card.className = 'album-card';
    card.innerHTML = `
      <div class="album-card-art" style="${albumArtStyle(album)}">
        ${album.emoji}
        <button class="album-card-play">
          <svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
        </button>
      </div>
      <div class="album-card-name">${album.name}</div>
      <div class="album-card-year">${album.year}</div>
    `;
    card.addEventListener('click', e => {
      if (e.target.closest('.album-card-play')) {
        playSong(songs[0]);
      } else {
        showAlbum(album.id);
      }
    });
    fc.appendChild(card);
  });

  const list = $('home-song-list');
  list.innerHTML = '';
  SONGS.forEach((s, i) => list.appendChild(buildSongRow(s, i + 1, true)));
}

function renderLibrary() {
  const el = $('library-content');
  el.innerHTML = '';
  ALBUMS.forEach(album => {
    const songs = SONGS.filter(s => s.album === album.id);
    if (!songs.length) return;
    const sec = document.createElement('div');
    sec.className = 'library-album-section';
    sec.innerHTML = `
      <div class="library-album-header">
        <div class="library-album-art" style="${albumArtStyle(album)}">${album.emoji}</div>
        <div class="library-album-text">
          <h3>${album.name}</h3>
          <p>${album.year} · ${songs.length} tracks</p>
        </div>
      </div>
      <div class="song-list library-song-list-${album.id}"></div>
    `;
    sec.querySelector('.library-album-header').addEventListener('click', () => showAlbum(album.id));
    el.appendChild(sec);
    const list = sec.querySelector(`.library-song-list-${album.id}`);
    songs.forEach((s, i) => list.appendChild(buildSongRow(s, i + 1)));
  });
}

function showAlbum(albumId) {
  const album = albumById(albumId);
  const songs = SONGS.filter(s => s.album === albumId);
  $('album-hero-art').style.cssText = albumArtStyle(album);
  $('album-hero-art').textContent = album.emoji;
  $('album-hero-title').textContent = album.name;
  $('album-hero-meta').textContent = `${album.year} · ${songs.length} songs`;
  const list = $('album-song-list');
  list.innerHTML = '';
  songs.forEach((s, i) => list.appendChild(buildSongRow(s, i + 1)));
  showView('album');
  state.currentAlbum = albumId;
  document.querySelectorAll('.album-sidebar-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.album === albumId);
  });
}

function renderSidebar() {
  const el = $('album-list');
  ALBUMS.forEach(album => {
    if (!SONGS.some(s => s.album === album.id)) return;
    const btn = document.createElement('button');
    btn.className = 'album-sidebar-btn';
    btn.textContent = album.name;
    btn.dataset.album = album.id;
    btn.addEventListener('click', () => showAlbum(album.id));
    el.appendChild(btn);
  });
}

/* ── Search ─────────────────────────────────────────────────────────────── */

function doSearch(query) {
  const q = query.trim().toLowerCase();
  const results = $('search-results');
  const noRes = $('no-results');
  const hint = $('search-hint');
  results.innerHTML = '';

  if (!q) {
    noRes.classList.add('hidden');
    hint.style.display = '';
    return;
  }

  hint.style.display = 'none';

  const matches = [];
  SONGS.forEach(song => {
    const album = albumById(song.album);
    const titleMatch = song.title.toLowerCase().includes(q);
    const albumMatch = album.name.toLowerCase().includes(q);
    const lyricLine = song.lyrics.find(l => l.l.toLowerCase().includes(q));

    if (titleMatch || albumMatch || lyricLine) {
      matches.push({ song, lyricLine: lyricLine?.l || null });
    }
  });

  if (!matches.length) {
    noRes.classList.remove('hidden');
    $('no-results-query').textContent = query;
    return;
  }

  noRes.classList.add('hidden');
  matches.forEach(({ song, lyricLine }, i) => {
    let snippet = null;
    if (lyricLine) {
      const idx = lyricLine.toLowerCase().indexOf(q);
      const start = Math.max(0, idx - 20);
      const end = Math.min(lyricLine.length, idx + q.length + 20);
      snippet = '...' + lyricLine.slice(start, end).replace(
        new RegExp(q, 'gi'),
        m => `<mark style="background:rgba(29,185,84,.3);color:#fff;border-radius:2px">${m}</mark>`
      ) + '...';
    }
    results.appendChild(buildSongRow(song, i + 1, true, snippet));
  });
}

/* ── Player ─────────────────────────────────────────────────────────────── */

function playSong(song) {
  state.currentSong = song;
  state.elapsed = 0;
  state.playing = true;
  state.activeLyricIdx = -1;

  const album = albumById(song.album);

  $('player-title').textContent = song.title;
  $('player-art').style.cssText = albumArtStyle(album);
  $('player-art').textContent = album.emoji;

  $('btn-play').querySelector('.icon-play').classList.add('hidden');
  $('btn-play').querySelector('.icon-pause').classList.remove('hidden');

  $('time-total').textContent = fmt(song.duration);
  $('time-elapsed').textContent = '0:00';
  $('progress-fill').style.width = '0%';
  $('progress-knob').style.left = '0%';

  if (state.lyricsPanelOpen) renderLyricsPanel();
  refreshSongListHighlight();
  startTicker();
}

function togglePlay() {
  if (!state.currentSong) return;
  state.playing = !state.playing;
  $('btn-play').querySelector('.icon-play').classList.toggle('hidden', state.playing);
  $('btn-play').querySelector('.icon-pause').classList.toggle('hidden', !state.playing);
  if (state.playing) startTicker(); else stopTicker();
}

function startTicker() {
  stopTicker();
  state.ticker = setInterval(() => {
    if (!state.playing || !state.currentSong) return;
    state.elapsed += 0.5;
    if (state.elapsed >= state.currentSong.duration) {
      if (state.repeat) {
        state.elapsed = 0;
      } else {
        nextSong();
        return;
      }
    }
    updateProgressUI();
    updateActiveLyric();
  }, 500);
}

function stopTicker() {
  if (state.ticker) { clearInterval(state.ticker); state.ticker = null; }
}

function updateProgressUI() {
  const pct = (state.elapsed / state.currentSong.duration) * 100;
  $('progress-fill').style.width = pct + '%';
  $('progress-knob').style.left = pct + '%';
  $('time-elapsed').textContent = fmt(state.elapsed);
}

function seekTo(pct) {
  if (!state.currentSong) return;
  state.elapsed = (pct / 100) * state.currentSong.duration;
  state.activeLyricIdx = -1;
  updateProgressUI();
  updateActiveLyric();
}

function nextSong() {
  if (!state.currentSong) return;
  const idx = SONGS.findIndex(s => s.id === state.currentSong.id);
  const next = state.shuffle
    ? SONGS[Math.floor(Math.random() * SONGS.length)]
    : SONGS[(idx + 1) % SONGS.length];
  playSong(next);
}

function prevSong() {
  if (!state.currentSong) return;
  if (state.elapsed > 4) { state.elapsed = 0; updateProgressUI(); return; }
  const idx = SONGS.findIndex(s => s.id === state.currentSong.id);
  const prev = SONGS[(idx - 1 + SONGS.length) % SONGS.length];
  playSong(prev);
}

function refreshSongListHighlight() {
  document.querySelectorAll('.song-row').forEach(row => {
    row.classList.toggle('playing', +row.dataset.songId === state.currentSong?.id);
  });
}

/* ── Live Lyric Sync ─────────────────────────────────────────────────────── */

function updateActiveLyric() {
  if (!state.currentSong || !state.lyricsPanelOpen) return;
  const lyrics = state.currentSong.lyrics;
  let idx = -1;
  for (let i = 0; i < lyrics.length; i++) {
    if (state.elapsed >= lyrics[i].t) idx = i;
    else break;
  }
  if (idx === state.activeLyricIdx) return;
  state.activeLyricIdx = idx;
  highlightLyricLine(idx);
}

function highlightLyricLine(idx) {
  const lines = document.querySelectorAll('.lyric-line');
  lines.forEach((el, i) => {
    el.classList.remove('active', 'passed');
    if (i < idx) el.classList.add('passed');
    if (i === idx) el.classList.add('active');
  });
  if (idx >= 0 && lines[idx]) {
    const body = $('lyrics-body');
    const line = lines[idx];
    const bodyRect = body.getBoundingClientRect();
    const lineRect = line.getBoundingClientRect();
    const target = body.scrollTop + (lineRect.top - bodyRect.top) - (body.clientHeight / 2) + (line.clientHeight / 2);
    body.scrollTo({ top: target, behavior: 'smooth' });
  }
}

function renderLyricsPanel() {
  const song = state.currentSong;
  const album = song ? albumById(song.album) : null;

  $('np-title').textContent = song ? song.title : 'No song playing';
  $('np-album').textContent = album ? album.name : '—';
  $('np-art').style.cssText = album ? albumArtStyle(album) : '';
  $('np-art').textContent = album ? album.emoji : '';

  const container = $('lyrics-lines');
  if (!song || !song.lyrics.length) {
    container.innerHTML = '<p class="lyrics-idle">No lyrics available.</p>';
    return;
  }

  container.innerHTML = '';
  song.lyrics.forEach((entry, i) => {
    if (!entry.l.trim()) {
      const blank = document.createElement('div');
      blank.className = 'lyric-blank';
      container.appendChild(blank);
      return;
    }
    const el = document.createElement('div');
    el.className = 'lyric-line';
    el.textContent = entry.l;
    el.addEventListener('click', () => {
      state.elapsed = entry.t;
      state.activeLyricIdx = -1;
      updateProgressUI();
      updateActiveLyric();
    });
    container.appendChild(el);
  });

  $('lyrics-fetched-time').textContent = 'Synced live';
  highlightLyricLine(state.activeLyricIdx);
}

function openLyricsPanel() {
  state.lyricsPanelOpen = true;
  $('lyrics-panel').classList.add('open');
  $('lyrics-toggle').classList.add('active');
  document.body.classList.add('lyrics-open');
  renderLyricsPanel();
}

function closeLyricsPanel() {
  state.lyricsPanelOpen = false;
  $('lyrics-panel').classList.remove('open');
  $('lyrics-toggle').classList.remove('active');
  document.body.classList.remove('lyrics-open');
}

/* ── Live update simulation ─────────────────────────────────────────────── */

function simulateLiveUpdate() {
  const badge = $('sidebar-update');
  const txt = $('update-text');
  const messages = [
    'Scanning Genius for new lyrics...',
    'Comparing 3 lyric sources...',
    'Lyrics verified — database updated.',
    'New Eminem freestyle detected...',
    'Timestamping lyric lines...',
    'All lyrics up to date.',
  ];
  let mi = 0;
  badge.style.display = 'flex';
  txt.textContent = messages[mi];
  const iv = setInterval(() => {
    mi++;
    if (mi >= messages.length) {
      clearInterval(iv);
      setTimeout(() => { badge.style.display = 'none'; }, 3000);
      return;
    }
    txt.textContent = messages[mi];
  }, 1800);
}

/* ── Init ─────────────────────────────────────────────────────────────── */

function init() {
  renderSidebar();
  renderHome();
  renderLibrary();

  // nav
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      showView(btn.dataset.view);
      if (btn.dataset.view === 'home') renderHome();
    });
  });

  // search
  const si = $('search-input');
  si.addEventListener('input', () => {
    const q = si.value;
    $('clear-search').classList.toggle('hidden', !q);
    doSearch(q);
  });
  $('clear-search').addEventListener('click', () => {
    si.value = '';
    $('clear-search').classList.add('hidden');
    doSearch('');
    si.focus();
  });

  // player controls
  $('btn-play').addEventListener('click', togglePlay);
  $('btn-next').addEventListener('click', nextSong);
  $('btn-prev').addEventListener('click', prevSong);
  $('btn-shuffle').addEventListener('click', () => {
    state.shuffle = !state.shuffle;
    $('btn-shuffle').dataset.active = state.shuffle;
  });
  $('btn-repeat').addEventListener('click', () => {
    state.repeat = !state.repeat;
    $('btn-repeat').dataset.active = state.repeat;
  });

  // progress seek
  const pb = $('progress-bar');
  pb.addEventListener('click', e => {
    const rect = pb.getBoundingClientRect();
    seekTo(((e.clientX - rect.left) / rect.width) * 100);
  });

  // volume
  $('volume-slider').addEventListener('input', e => {
    state.volume = +e.target.value;
  });

  // lyrics panel
  $('lyrics-toggle').addEventListener('click', () => {
    state.lyricsPanelOpen ? closeLyricsPanel() : openLyricsPanel();
  });
  $('lyrics-close').addEventListener('click', closeLyricsPanel);

  // auto-play first song on load
  playSong(SONGS[4]); // Lose Yourself
  openLyricsPanel();

  // simulate a live update after 8 seconds
  setTimeout(simulateLiveUpdate, 8000);
  // repeat every 90 seconds
  setInterval(simulateLiveUpdate, 90000);
}

document.addEventListener('DOMContentLoaded', init);
